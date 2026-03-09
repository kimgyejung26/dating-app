import 'package:cloud_firestore/cloud_firestore.dart';

class ChatService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  String buildDirectRoomId(String userA, String userB) {
    final ids = [userA, userB]..sort();
    return 'dm_${ids[0]}_${ids[1]}';
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> messagesStream(String roomId) {
    return _firestore
        .collection('chat_rooms')
        .doc(roomId)
        .collection('messages')
        .orderBy('createdAt', descending: false)
        .snapshots();
  }

  Future<void> ensureDirectRoom({
    required String currentUserId,
    required String partnerId,
    required String currentUserName,
    required String partnerName,
    String? currentUserAvatarUrl,
    String? partnerAvatarUrl,
  }) async {
    final roomId = buildDirectRoomId(currentUserId, partnerId);
    final roomRef = _firestore.collection('chat_rooms').doc(roomId);

    final participantIds = [currentUserId, partnerId]..sort();

    final payload = {
      'roomId': roomId,
      'participantIds': participantIds,
      'updatedAt': FieldValue.serverTimestamp(),
      'participantInfo': {
        currentUserId: {
          'nickname': currentUserName,
          'avatarUrl': currentUserAvatarUrl ?? '',
        },
        partnerId: {
          'nickname': partnerName,
          'avatarUrl': partnerAvatarUrl ?? '',
        },
      },
    };

    final snap = await roomRef.get();

    if (!snap.exists) {
      await roomRef.set({
        ...payload,
        'createdAt': FieldValue.serverTimestamp(),
        'lastMessage': '',
        'lastMessageAt': null,
      });
      return;
    }

    await roomRef.set(payload, SetOptions(merge: true));
  }

  Future<void> sendTextMessage({
    required String roomId,
    required String senderId,
    required String text,
  }) async {
    final roomRef = _firestore.collection('chat_rooms').doc(roomId);
    final msgRef = roomRef.collection('messages').doc();

    final batch = _firestore.batch();

    batch.set(msgRef, {
      'senderId': senderId,
      'text': text,
      'type': 'text',
      'createdAt': FieldValue.serverTimestamp(),
    });

    batch.set(roomRef, {
      'lastMessage': text,
      'lastMessageAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await batch.commit();
  }

  Future<void> sendFakeAutoReply({
    required String roomId,
    required String text,
  }) async {
    const replies = [
      '오 좋네요 ㅎㅎ',
      '그 얘기 더 해주세요!',
      '저도 그거 좋아해요 🙂',
      '채팅 이어가볼까요?',
      '좋아요! 언제가 편하세요?',
    ];

    final reply = replies[text.length % replies.length];

    await sendTextMessage(roomId: roomId, senderId: 'fake_user_1', text: reply);
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> chatRoomsStream(String userId) {
    return _firestore
        .collection('chat_rooms')
        .where('participantIds', arrayContains: userId)
        .snapshots();
  }

  Future<DocumentSnapshot<Map<String, dynamic>>?> getUserProfileDoc(
    String userId,
  ) async {
    try {
      return await _firestore.collection('users').doc(userId).get();
    } catch (_) {
      return null;
    }
  }
}
