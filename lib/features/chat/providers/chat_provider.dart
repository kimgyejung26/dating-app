import 'package:flutter/cupertino.dart';

/// 채팅 상태 관리 Provider
class ChatProvider extends ChangeNotifier {
  bool _isLoading = false;
  List<dynamic> _chatRooms = [];
  List<dynamic> _messages = [];

  bool get isLoading => _isLoading;
  List<dynamic> get chatRooms => _chatRooms;
  List<dynamic> get messages => _messages;

  /// 채팅방 목록 로드
  Future<void> loadChatRooms() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _chatRooms = []; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 메시지 로드
  Future<void> loadMessages(String roomId) async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(milliseconds: 500));
      _messages = []; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 메시지 전송
  Future<void> sendMessage(String roomId, String content) async {
    // TODO: 구현
  }
}
