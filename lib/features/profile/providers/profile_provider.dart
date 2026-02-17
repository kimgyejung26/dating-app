import 'package:flutter/cupertino.dart';

/// 프로필 상태 관리 Provider
class ProfileProvider extends ChangeNotifier {
  bool _isLoading = false;
  int _heartBalance = 0;
  List<dynamic> _receivedHearts = [];
  List<dynamic> _friends = [];

  bool get isLoading => _isLoading;
  int get heartBalance => _heartBalance;
  List<dynamic> get receivedHearts => _receivedHearts;
  List<dynamic> get friends => _friends;

  /// 프로필 데이터 로드
  Future<void> loadProfile() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _heartBalance = 10; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 받은 하트 목록 로드
  Future<void> loadReceivedHearts() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _receivedHearts = []; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 친구 목록 로드
  Future<void> loadFriends() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _friends = []; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
