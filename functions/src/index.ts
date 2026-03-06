/**
 * 설레연 Cloud Functions
 *
 * 트리거 목록:
 *   1) onRecEventCreated  — recEvents 이벤트 로깅 + 매치 체크
 *   2) onInteractionCreated — interactions like/super_like → 매치 생성 + 채팅방
 *   3) onCommentCreated — 대나무숲 댓글 수 동기화
 *   4) onMatchUpdated — 매치 해제 시 채팅방 비활성화
 */

import { setGlobalOptions } from "firebase-functions/v2";
import { onDocumentCreated } from "firebase-functions/v2/firestore";
import { onDocumentUpdated } from "firebase-functions/v2/firestore";
import * as logger from "firebase-functions/logger";
import { initializeApp } from "firebase-admin/app";
import { getFirestore, FieldValue } from "firebase-admin/firestore";

// Firebase Admin 초기화
initializeApp();
const db = getFirestore();

// 전역 옵션: 리전 서울(asia-northeast3), 최대 인스턴스 10개
setGlobalOptions({ region: "asia-northeast3", maxInstances: 10 });

// =============================================================================
// 1) recEvents onCreate 트리거
// =============================================================================
export const onRecEventCreated = onDocumentCreated(
    "recEvents/{docId}",
    async (event) => {
        const snap = event.data;
        if (!snap) {
            logger.warn("No data in recEvent document");
            return;
        }

        const data = snap.data();
        const { userId, targetUserId, eventType, source } = data;

        logger.info("📝 recEvent created", {
            docId: event.params.docId,
            userId,
            targetUserId,
            eventType,
            source,
        });

        // like / swipe_right 이벤트 → 매치 체크
        if (eventType === "like" || eventType === "swipe_right") {
            await checkAndCreateRecMatch(userId, targetUserId, eventType);
        }
    }
);

// =============================================================================
// 2) 매치 판정 — interactions 문서 생성 시 트리거
//    like/super_like가 기록되면 상대방도 like했는지 체크 → 매치 성사
// =============================================================================
export const onInteractionCreated = onDocumentCreated(
    "interactions/{interactionId}",
    async (event) => {
        const snap = event.data;
        if (!snap) return;

        const data = snap.data();
        const { fromUserId, toUserId, action } = data;

        if (action !== "like" && action !== "super_like") return;

        // 상대방 → 나에게 like/super_like 했는지 조회
        const reverseQuery = await db
            .collection("interactions")
            .where("fromUserId", "==", toUserId)
            .where("toUserId", "==", fromUserId)
            .where("action", "in", ["like", "super_like"])
            .limit(1)
            .get();

        if (reverseQuery.empty) return;

        // 이미 매치가 존재하는지 확인
        const existingMatch = await db
            .collection("matches")
            .where("userIds", "array-contains", fromUserId)
            .get();

        for (const doc of existingMatch.docs) {
            const ids = doc.data().userIds || [];
            if (ids.includes(toUserId)) {
                logger.info(`Match already exists: ${doc.id}`);
                return;
            }
        }

        // 매치 생성
        const matchRef = db.collection("matches").doc();
        const matchId = matchRef.id;

        // 채팅방 생성
        const roomRef = db.collection("chat_rooms").doc();
        const roomId = roomRef.id;

        // 양측 유저 프로필 조회
        const [userADoc, userBDoc] = await Promise.all([
            db.collection("users").doc(fromUserId).get(),
            db.collection("users").doc(toUserId).get(),
        ]);

        const userAData = userADoc.data() || {};
        const userBData = userBDoc.data() || {};

        const participants = [
            {
                id: fromUserId,
                nickname: userAData.nickname || "유저",
                profileImageUrl: userAData.profileImageUrl || null,
            },
            {
                id: toUserId,
                nickname: userBData.nickname || "유저",
                profileImageUrl: userBData.profileImageUrl || null,
            },
        ];

        const batch = db.batch();

        // 매치 문서
        batch.set(matchRef, {
            userIds: [fromUserId, toUserId],
            matchType: "mutual_like",
            matchedAt: FieldValue.serverTimestamp(),
            status: "active",
            chatRoomId: roomId,
        });

        // 채팅방 문서
        batch.set(roomRef, {
            type: "one_to_one",
            participantIds: [fromUserId, toUserId],
            participants: participants,
            matchId: matchId,
            lastMessage: {
                content: "매칭이 성사되었어요! 먼저 인사해보세요 💕",
                senderId: "system",
                type: "system",
                createdAt: FieldValue.serverTimestamp(),
            },
            createdAt: FieldValue.serverTimestamp(),
            updatedAt: FieldValue.serverTimestamp(),
        });

        // 시스템 메시지
        const msgRef = roomRef.collection("messages").doc();
        batch.set(msgRef, {
            senderId: "system",
            content: "매칭이 성사되었어요! 먼저 인사해보세요 💕",
            type: "system",
            readBy: [],
            createdAt: FieldValue.serverTimestamp(),
        });

        await batch.commit();
        logger.info(`Match created: ${matchId}, ChatRoom: ${roomId}`);
    }
);

// =============================================================================
// 3) 대나무숲 댓글 수 동기화
// =============================================================================
export const onCommentCreated = onDocumentCreated(
    "posts/{postId}/comments/{commentId}",
    async (event) => {
        const postId = event.params.postId;
        await db
            .collection("posts")
            .doc(postId)
            .update({ commentCount: FieldValue.increment(1) });
    }
);

// =============================================================================
// 4) 매치 해제 시 채팅방 비활성화
// =============================================================================
export const onMatchUpdated = onDocumentUpdated(
    "matches/{matchId}",
    async (event) => {
        const before = event.data?.before.data();
        const after = event.data?.after.data();

        if (!before || !after) return;

        if (before.status === "active" && after.status === "unmatched") {
            const chatRoomId = after.chatRoomId;
            if (!chatRoomId) return;

            await db.collection("chat_rooms").doc(chatRoomId).update({
                status: "closed",
                closedAt: FieldValue.serverTimestamp(),
            });

            await db
                .collection("chat_rooms")
                .doc(chatRoomId)
                .collection("messages")
                .add({
                    senderId: "system",
                    content: "매칭이 해제되었습니다.",
                    type: "system",
                    readBy: [],
                    createdAt: FieldValue.serverTimestamp(),
                });
        }
    }
);

// =============================================================================
// recEvents 매치 체크 헬퍼
// =============================================================================
async function checkAndCreateRecMatch(
    userA: string,
    userB: string,
    matchType: string
): Promise<string | null> {
    const reverseQuery = await db
        .collection("recEvents")
        .where("userId", "==", userB)
        .where("targetUserId", "==", userA)
        .where("eventType", "in", ["like", "swipe_right"])
        .limit(1)
        .get();

    if (reverseQuery.empty) {
        logger.info("❌ No mutual like found", { userA, userB });
        return null;
    }

    const existingMatch = await db
        .collection("matches")
        .where("userIds", "array-contains", userA)
        .get();

    for (const doc of existingMatch.docs) {
        const ids = doc.data().userIds as string[];
        if (ids.includes(userB)) {
            logger.info("⚡ Match already exists", { matchId: doc.id });
            return doc.id;
        }
    }

    const matchRef = await db.collection("matches").add({
        userIds: [userA, userB],
        matchType: matchType,
        matchedAt: FieldValue.serverTimestamp(),
        status: "active",
        chatRoomId: null,
    });

    logger.info("🎉 Match created!", {
        matchId: matchRef.id,
        userA,
        userB,
        matchType,
    });

    return matchRef.id;
}
