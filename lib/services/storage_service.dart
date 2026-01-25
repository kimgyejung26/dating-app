import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const String _userIdKey = 'user_id';
  static const String _kakaoUserIdKey = 'kakao_user_id';
  static const String _isFirstLaunchKey = 'is_first_launch';
  static const String _hasSeenTutorialKey = 'has_seen_tutorial';
  static const String _studentEmailKeyPrefix = 'student_email_';
  static const String _studentVerifiedKeyPrefix = 'student_verified_';

  Future<void> saveUserId(String userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userIdKey, userId);
  }

  Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userIdKey);
  }

  Future<void> clearUserId() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userIdKey);
  }

  Future<void> saveKakaoUserId(String kakaoUserId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kakaoUserIdKey, kakaoUserId);
  }

  Future<String?> getKakaoUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kakaoUserIdKey);
  }

  Future<void> clearKakaoUserId() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kakaoUserIdKey);
  }

  Future<bool> isFirstLaunch() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_isFirstLaunchKey) ?? true;
  }

  Future<void> setFirstLaunchComplete() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_isFirstLaunchKey, false);
  }

  Future<bool> hasSeenTutorial() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_hasSeenTutorialKey) ?? false;
  }

  Future<void> setTutorialSeen() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_hasSeenTutorialKey, true);
  }

  Future<void> saveStudentEmail(String kakaoUserId, String email) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_studentEmailKeyPrefix$kakaoUserId', email);
  }

  Future<String?> getStudentEmail(String kakaoUserId) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('$_studentEmailKeyPrefix$kakaoUserId');
  }

  Future<void> setStudentVerified(String kakaoUserId, bool isVerified) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('$_studentVerifiedKeyPrefix$kakaoUserId', isVerified);
  }

  Future<bool> isStudentVerified(String kakaoUserId) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('$_studentVerifiedKeyPrefix$kakaoUserId') ?? false;
  }

  Future<void> clearStudentVerification(String kakaoUserId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_studentEmailKeyPrefix$kakaoUserId');
    await prefs.remove('$_studentVerifiedKeyPrefix$kakaoUserId');
  }
}
