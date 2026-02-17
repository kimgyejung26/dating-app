import 'dart:convert';

/// 로컬 스토리지 (메모리 기반 - 실제 앱에서는 shared_preferences 사용)
///
/// 실제 앱에서 사용하려면:
/// 1. pubspec.yaml에 shared_preferences 추가
/// 2. 이 파일을 shared_preferences 버전으로 교체
class LocalStorage {
  static LocalStorage? _instance;
  final Map<String, dynamic> _storage = {};

  LocalStorage._();

  static LocalStorage getInstance() {
    _instance ??= LocalStorage._();
    return _instance!;
  }

  // Auth tokens
  static const String _keyAccessToken = 'access_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyUserId = 'user_id';

  // User preferences
  static const String _keyOnboardingCompleted = 'onboarding_completed';
  static const String _keyTutorialShown = 'tutorial_shown';
  static const String _keyNotificationsEnabled = 'notifications_enabled';

  /// Access Token 저장
  Future<void> setAccessToken(String token) async {
    _storage[_keyAccessToken] = token;
  }

  /// Access Token 조회
  String? getAccessToken() {
    return _storage[_keyAccessToken] as String?;
  }

  /// Refresh Token 저장
  Future<void> setRefreshToken(String token) async {
    _storage[_keyRefreshToken] = token;
  }

  /// Refresh Token 조회
  String? getRefreshToken() {
    return _storage[_keyRefreshToken] as String?;
  }

  /// User ID 저장
  Future<void> setUserId(String userId) async {
    _storage[_keyUserId] = userId;
  }

  /// User ID 조회
  String? getUserId() {
    return _storage[_keyUserId] as String?;
  }

  /// 온보딩 완료 여부 저장
  Future<void> setOnboardingCompleted(bool completed) async {
    _storage[_keyOnboardingCompleted] = completed;
  }

  /// 온보딩 완료 여부 조회
  bool isOnboardingCompleted() {
    return _storage[_keyOnboardingCompleted] as bool? ?? false;
  }

  /// 튜토리얼 표시 여부 저장
  Future<void> setTutorialShown(bool shown) async {
    _storage[_keyTutorialShown] = shown;
  }

  /// 튜토리얼 표시 여부 조회
  bool isTutorialShown() {
    return _storage[_keyTutorialShown] as bool? ?? false;
  }

  /// 알림 설정 저장
  Future<void> setNotificationsEnabled(bool enabled) async {
    _storage[_keyNotificationsEnabled] = enabled;
  }

  /// 알림 설정 조회
  bool isNotificationsEnabled() {
    return _storage[_keyNotificationsEnabled] as bool? ?? true;
  }

  /// JSON 데이터 저장
  Future<void> setJson(String key, Map<String, dynamic> data) async {
    _storage[key] = jsonEncode(data);
  }

  /// JSON 데이터 조회
  Map<String, dynamic>? getJson(String key) {
    final jsonString = _storage[key] as String?;
    if (jsonString == null) return null;
    return jsonDecode(jsonString) as Map<String, dynamic>;
  }

  /// 로그아웃 시 초기화
  Future<void> clearAuth() async {
    _storage.remove(_keyAccessToken);
    _storage.remove(_keyRefreshToken);
    _storage.remove(_keyUserId);
  }

  /// 전체 초기화
  Future<void> clearAll() async {
    _storage.clear();
  }
}
