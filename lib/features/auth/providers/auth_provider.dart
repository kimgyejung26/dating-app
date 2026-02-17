import 'package:flutter/cupertino.dart';

/// 인증 상태 관리 Provider (기본 스텁)
class AuthProvider extends ChangeNotifier {
  bool _isLoading = false;
  bool _isLoggedIn = false;
  String? _accessToken;
  String? _errorMessage;

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _isLoggedIn;
  String? get accessToken => _accessToken;
  String? get errorMessage => _errorMessage;

  /// 카카오 로그인
  Future<bool> loginWithKakao(String kakaoToken) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _isLoggedIn = true;
      _accessToken = 'mock_token';
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// 로그아웃
  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출 및 토큰 삭제
      await Future.delayed(const Duration(milliseconds: 500));
      _isLoggedIn = false;
      _accessToken = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
