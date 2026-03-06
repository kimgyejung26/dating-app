/**
 * recEvents 데이터를 CSV로 내보내는 스크립트
 *
 * Firebase Admin SDK 사용 (보안 규칙 우회, 서비스 계정 키 필요)
 *
 * 사용법:
 *   1. Firebase Console → 프로젝트 설정 → 서비스 계정 → '새 비공개 키 생성' 클릭
 *   2. 다운로드된 JSON 파일을 functions 폴더에 serviceAccountKey.json으로 저장
 *   3. 실행:
 *      cd functions
 *      node export_rec_events.js              ← 전체
 *      node export_rec_events.js <userId>     ← 특정 유저만
 *
 * 결과 파일: functions/recEvents_export.csv
 */

const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const fs = require("fs");
const path = require("path");

// 서비스 계정 키 파일 찾기
const keyPath = path.join(__dirname, "serviceAccountKey.json");
if (!fs.existsSync(keyPath)) {
    console.error("❌ serviceAccountKey.json 파일이 없습니다!\n");
    console.error("📋 다운로드 방법:");
    console.error("   1. https://console.firebase.google.com 접속");
    console.error("   2. seolleyeon 프로젝트 선택");
    console.error("   3. ⚙️ 프로젝트 설정 → 서비스 계정 탭");
    console.error("   4. 'Node.js' 선택 → '새 비공개 키 생성' 클릭");
    console.error(`   5. 다운로드된 파일을 ${keyPath} 으로 저장\n`);
    process.exit(1);
}

// Firebase Admin 초기화
initializeApp({
    credential: cert(require(keyPath)),
});
const db = getFirestore();

async function exportRecEvents(targetUserId) {
    const rows = [];
    rows.push(["userId", "eventId", "targetUserId", "eventType", "source", "metadata", "createdAt"].join(","));

    let totalEvents = 0;

    // ───────────────────────────────────────────────────────────────────
    // (A) 구 구조: recEvents/{auto-id}
    // ───────────────────────────────────────────────────────────────────
    console.log("📁 [구 구조] recEvents/{auto-id} 조회 중...");

    let oldQuery = db.collection("recEvents").orderBy("createdAt", "asc");
    if (targetUserId) {
        oldQuery = oldQuery.where("userId", "==", targetUserId);
    }

    const oldSnap = await oldQuery.get();
    for (const doc of oldSnap.docs) {
        const d = doc.data();
        // 서브컬렉션 부모 문서(필드 없음) 스킵
        if (!d.eventType) continue;

        const createdAt = d.createdAt ? d.createdAt.toDate().toISOString() : "";
        const metadata = d.metadata ? JSON.stringify(d.metadata).replace(/"/g, '""') : "";

        rows.push([
            d.userId || "",
            doc.id,
            d.targetUserId || "",
            d.eventType || "",
            d.source || "",
            `"${metadata}"`,
            createdAt,
        ].join(","));
        totalEvents++;
    }

    console.log(`   → 구 구조 이벤트: ${totalEvents}건`);

    // ───────────────────────────────────────────────────────────────────
    // (B) 신 구조: recEvents/{userId}/events/{auto-id}
    // ───────────────────────────────────────────────────────────────────
    console.log("\n📁 [신 구조] recEvents/{userId}/events/{auto-id} 조회 중...");
    let newEvents = 0;

    // 유저 목록 조회
    const userDocs = await db.collection("recEvents").listDocuments();
    let userIds = userDocs.map((d) => d.id);

    if (targetUserId) {
        userIds = userIds.filter((id) => id === targetUserId);
    }

    for (const userId of userIds) {
        const eventsSnap = await db
            .collection("recEvents")
            .doc(userId)
            .collection("events")
            .orderBy("createdAt", "asc")
            .get();

        for (const doc of eventsSnap.docs) {
            const d = doc.data();
            const createdAt = d.createdAt ? d.createdAt.toDate().toISOString() : "";
            const metadata = d.metadata ? JSON.stringify(d.metadata).replace(/"/g, '""') : "";

            rows.push([
                userId,
                doc.id,
                d.targetUserId || "",
                d.eventType || "",
                d.source || "",
                `"${metadata}"`,
                createdAt,
            ].join(","));
            newEvents++;
        }
    }

    totalEvents += newEvents;
    console.log(`   → 신 구조 이벤트: ${newEvents}건`);

    // CSV 파일 저장
    const outputPath = path.join(__dirname, "recEvents_export.csv");
    const bom = "\uFEFF";
    fs.writeFileSync(outputPath, bom + rows.join("\n"), "utf8");

    console.log(`\n✅ 내보내기 완료!`);
    console.log(`   총 이벤트: ${totalEvents}건`);
    console.log(`   파일 위치: ${outputPath}`);
}

const targetUserId = process.argv[2] || null;
exportRecEvents(targetUserId).catch((err) => {
    console.error("❌ 내보내기 실패:", err.message);
    process.exit(1);
});
