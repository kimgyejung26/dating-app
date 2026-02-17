// =============================================================================
// 채팅방 데이터 모델
// 경로: lib/features/chat/models/chat_room_data.dart
//
// Firebase 연동 시 Firestore 문서와 1:1 매핑할 수 있도록 구성.
// fromMap / toMap 메서드로 직렬화/역직렬화 지원.
// =============================================================================

/// 채팅방으로 전달되는 데이터 모델.
///
/// Firebase 연동 시:
/// - `chatRoomId` → Firestore 'chatRooms' 컬렉션의 문서 ID
/// - `partnerId`  → Firestore 'users' 컬렉션의 문서 ID
/// - 나머지 필드는 UI 표시용 스냅샷 (캐시)
class ChatRoomData {
  /// Firestore chatRooms/{chatRoomId}
  final String chatRoomId;

  /// 상대방 유저 ID (Firestore users/{partnerId})
  final String partnerId;

  /// 상대방 이름 (UI 표시용)
  final String partnerName;

  /// 상대방 대학교 (UI 표시용)
  final String partnerUniversity;

  /// 상대방 아바타 URL (UI 표시용)
  final String? partnerAvatarUrl;

  /// 마지막 메시지 미리보기 (UI 표시용)
  final String? lastMessage;

  /// 마지막 메시지 시간 (UI 표시용)
  final String? lastMessageTime;

  const ChatRoomData({
    required this.chatRoomId,
    required this.partnerId,
    required this.partnerName,
    this.partnerUniversity = '',
    this.partnerAvatarUrl,
    this.lastMessage,
    this.lastMessageTime,
  });

  /// Firestore 문서 → ChatRoomData
  factory ChatRoomData.fromMap(Map<String, dynamic> map, {String? docId}) {
    return ChatRoomData(
      chatRoomId: docId ?? map['chatRoomId'] as String? ?? '',
      partnerId: map['partnerId'] as String? ?? '',
      partnerName: map['partnerName'] as String? ?? '',
      partnerUniversity: map['partnerUniversity'] as String? ?? '',
      partnerAvatarUrl: map['partnerAvatarUrl'] as String?,
      lastMessage: map['lastMessage'] as String?,
      lastMessageTime: map['lastMessageTime'] as String?,
    );
  }

  /// ChatRoomData → Firestore 문서
  Map<String, dynamic> toMap() {
    return {
      'chatRoomId': chatRoomId,
      'partnerId': partnerId,
      'partnerName': partnerName,
      'partnerUniversity': partnerUniversity,
      'partnerAvatarUrl': partnerAvatarUrl,
      'lastMessage': lastMessage,
      'lastMessageTime': lastMessageTime,
    };
  }
}
