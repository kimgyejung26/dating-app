import '../models/chat/chat_room_model.dart';

/// 채팅 리포지토리
abstract class ChatRepository {
  /// 채팅방 목록 조회
  Future<List<ChatRoomModel>> getChatRooms();

  /// 채팅방 상세 조회
  Future<ChatRoomModel> getChatRoom(String roomId);

  /// 메시지 목록 조회
  Future<List<MessageModel>> getMessages(String roomId, {String? beforeId});

  /// 메시지 전송
  Future<MessageModel> sendMessage(String roomId, String content);

  /// 이미지 메시지 전송
  Future<MessageModel> sendImageMessage(String roomId, String imagePath);

  /// 메시지 읽음 처리
  Future<void> markAsRead(String roomId);

  /// 채팅방 나가기
  Future<void> leaveChatRoom(String roomId);
}
