import 'package:cloud_firestore/cloud_firestore.dart';

import '../../chat/services/chat_service.dart';

class ProfilePhotoAccessService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final ChatService _chatService = ChatService();

  Future<bool> canViewUnblurredProfilePhotos({
    required String viewerUserId,
    required String targetUserId,
  }) async {
    if (viewerUserId.isEmpty || targetUserId.isEmpty) {
      return false;
    }

    if (viewerUserId == targetUserId) {
      return true;
    }

    final roomId = _chatService.buildDirectRoomId(viewerUserId, targetUserId);
    final roomRef = _firestore.collection('chat_rooms').doc(roomId);
    // A user who has not opened a 1:1 chat yet is deliberately not a
    // participant of its deterministic room ID. The Firestore rule therefore
    // rejects this read instead of returning a non-existent snapshot. That is
    // the normal "photos still blurred" state, not an error for the profile
    // screen to surface.
    DocumentSnapshot<Map<String, dynamic>> roomSnap;
    try {
      roomSnap = await roomRef.get();
    } on FirebaseException catch (error) {
      if (error.code == 'permission-denied') {
        return false;
      }
      rethrow;
    }
    if (!roomSnap.exists) {
      return false;
    }

    final textMessageSnap = await roomRef
        .collection('messages')
        .where('type', isEqualTo: 'text')
        .limit(1)
        .get();

    if (textMessageSnap.docs.isEmpty) {
      return false;
    }

    // Gallery disclosure begins only after either participant has sent a
    // text message.  This read must not mutate the room: the sender writes
    // the chat metadata atomically with the message itself.
    return textMessageSnap.docs.isNotEmpty;
  }
}
