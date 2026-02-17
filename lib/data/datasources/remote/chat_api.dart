import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';

/// 채팅 API 데이터소스
class ChatApi {
  final ApiClient _client;

  ChatApi(this._client);

  /// 채팅방 목록 조회
  Future<Map<String, dynamic>> getChatRooms() async {
    return await _client.get(ApiEndpoints.chatRooms);
  }

  /// 메시지 목록 조회
  Future<Map<String, dynamic>> getMessages(
    String roomId, {
    String? beforeId,
  }) async {
    final query = beforeId != null ? '?beforeId=$beforeId' : '';
    return await _client.get('${ApiEndpoints.chatMessages}/$roomId$query');
  }

  /// 메시지 전송
  Future<Map<String, dynamic>> sendMessage(
    String roomId,
    String content,
  ) async {
    return await _client.post(
      ApiEndpoints.chatMessages,
      body: {'roomId': roomId, 'content': content},
    );
  }
}
