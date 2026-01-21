import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:uuid/uuid.dart';
import '../models/user_model.dart';
import 'user_service.dart';

class AuthService {
  // TODO: Uncomment when implementing actual API calls
  // final ApiService _apiService = ApiService();
  final _uuid = const Uuid();
  final _userService = UserService();

  Future<Map<String, dynamic>> loginWithKakao() async {
    try {
      if (kIsWeb) {
        // Web: JS SDK 기반 카카오 계정 로그인
        await UserApi.instance.loginWithKakaoAccount();
      } else {
        // Android/iOS: 네이티브 환경에서 카카오 계정 로그인
        await UserApi.instance.loginWithKakaoAccount();
      }
      final user = await UserApi.instance.me();

      final kakaoUserId = user.id.toString();

      final userInfo = {
        'id': kakaoUserId,
        'nickname': user.kakaoAccount?.profile?.nickname,
        'profileImageUrl': user.kakaoAccount?.profile?.profileImageUrl,
        'email': user.kakaoAccount?.email,
      };

      return userInfo;
    } on KakaoException catch (e) {
      final detail = e.message ?? e.toString();
      throw Exception('카카오 로그인 실패: $detail');
    } catch (e) {
      throw Exception('로그인 실패: $e');
    }
  }

  Future<bool> kakaoUserExists(String kakaoUserId) async {
    return await _userService.existsKakaoUser(kakaoUserId);
  }

  Future<bool> isInitialSetupComplete(String kakaoUserId) async {
    return await _userService.isInitialSetupComplete(kakaoUserId);
  }

  Future<bool> hasSeenTutorial(String kakaoUserId) async {
    return await _userService.hasSeenTutorial(kakaoUserId);
  }

  Future<void> setTutorialSeen(String kakaoUserId) async {
    await _userService.setTutorialSeen(kakaoUserId);
  }

  Future<UserModel?> signUp({
    required String phoneNumber,
    required String verificationCode,
    String? kakaoToken,
  }) async {
    try {
      // TODO: Implement actual API call
      // For now, return a mock user
      final user = UserModel(
        id: _uuid.v4(),
        phoneNumber: phoneNumber,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      // Simulate API call
      await Future.delayed(const Duration(seconds: 1));

      return user;
    } catch (e) {
      throw Exception('Sign up failed: $e');
    }
  }

  Future<bool> verifyStudent({
    required String userId,
    required String portalId,
    required String portalPassword,
  }) async {
    try {
      // TODO: Implement actual Yonsei Portal verification
      // For now, simulate verification
      await Future.delayed(const Duration(seconds: 1));
      return true;
    } catch (e) {
      throw Exception('Student verification failed: $e');
    }
  }

  Future<UserModel?> getUser(String userId) async {
    try {
      // TODO: Implement actual API call
      await Future.delayed(const Duration(milliseconds: 500));
      return null; // Return null if user not found
    } catch (e) {
      throw Exception('Get user failed: $e');
    }
  }

  Future<void> updateUser(UserModel user) async {
    try {
      // TODO: Implement actual API call
      await Future.delayed(const Duration(milliseconds: 500));
    } catch (e) {
      throw Exception('Update user failed: $e');
    }
  }
}
