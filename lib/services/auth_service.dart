import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:uuid/uuid.dart';

import '../models/user_model.dart';
import 'user_service.dart';

class AuthService {
  final _uuid = const Uuid();
  final _userService = UserService();
  final FirebaseAuth _firebaseAuth = FirebaseAuth.instance;

  /// ✅ 카카오 로그인
  /// - Web: 카카오 계정 로그인
  /// - Mobile(iOS/Android): 카카오톡 앱 우선 -> 실패/미설치 시 계정 로그인 fallback
  /// 반환: userInfo(Map) = {id, nickname, profileImageUrl, email}
  Future<Map<String, dynamic>> loginWithKakao() async {
    try {
      if (kIsWeb) {
        // Web: JS SDK 기반 카카오 계정 로그인
        await UserApi.instance.loginWithKakaoAccount();
      } else {
        // Mobile: 카카오톡 설치되어 있으면 카톡 앱 로그인 우선
        final installed = await isKakaoTalkInstalled();
        debugPrint('[Kakao] isKakaoTalkInstalled=$installed');
        if (installed) {
          try {
            await UserApi.instance.loginWithKakaoTalk();
          } on KakaoException catch (e) {
            final detail = e.message ?? e.toString();
            debugPrint('[Kakao] loginWithKakaoTalk failed: $detail');
            debugPrint('[Kakao] fallback to loginWithKakaoAccount');
            await UserApi.instance.loginWithKakaoAccount();
          } catch (e, st) {
            debugPrint('[Kakao] loginWithKakaoTalk unexpected error: $e');
            debugPrint(st.toString());
            debugPrint('[Kakao] fallback to loginWithKakaoAccount');
            await UserApi.instance.loginWithKakaoAccount();
          }
        } else {
          // 카톡 미설치 -> 계정 로그인
          await UserApi.instance.loginWithKakaoAccount();
        }
      }

      // 사용자 정보
      final user = await UserApi.instance.me();
      final kakaoUserId = user.id.toString();

      if (kakaoUserId.isEmpty) {
        throw Exception('카카오 사용자 ID를 가져오지 못했습니다.');
      }

      return {
        'id': kakaoUserId,
        'nickname': user.kakaoAccount?.profile?.nickname,
        'profileImageUrl': user.kakaoAccount?.profile?.profileImageUrl,
        'email': user.kakaoAccount?.email,
      };
    } on KakaoException catch (e) {
      final detail = e.message ?? e.toString();
      throw Exception('카카오 로그인 실패: $detail');
    } catch (e) {
      throw Exception('로그인 실패: $e');
    }
  }

  // -------------------------
  // 이하 기존 기능 (너 코드 유지)
  // -------------------------

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

  Future<bool> isStudentVerified(String kakaoUserId) async {
    return await _userService.isStudentVerified(kakaoUserId);
  }

  Future<String?> getStudentEmail(String kakaoUserId) async {
    return await _userService.getStudentEmail(kakaoUserId);
  }


  Future<void> setStudentVerified({
    required String kakaoUserId,
    required String studentEmail,
  }) async {
    await _userService.setStudentVerification(
      kakaoUserId: kakaoUserId,
      studentEmail: studentEmail,
    );
  }

  Future<void> sendStudentEmailLink({
    required String email,
    required String continueUrl,
  }) async {
    final acs = ActionCodeSettings(
      url: continueUrl,
      handleCodeInApp: true,
      iOSBundleId: 'com.yonsei.dating',
      androidPackageName: 'com.yonsei.dating', // TODO: 안드로이드 패키지명으로 바꿔
      androidInstallApp: true,
      androidMinimumVersion: '21',
    );

    await _firebaseAuth.sendSignInLinkToEmail(
      email: email,
      actionCodeSettings: acs,
    );
  }

  bool isSignInWithEmailLink(String link) {
    return _firebaseAuth.isSignInWithEmailLink(link);
  }

  Future<void> signInWithEmailLink({
    required String email,
    required String emailLink,
  }) async {
    await _firebaseAuth.signInWithEmailLink(email: email, emailLink: emailLink);
  }

  Future<UserModel?> signUp({
    required String phoneNumber,
    required String verificationCode,
    String? kakaoToken,
  }) async {
    try {
      final user = UserModel(
        id: _uuid.v4(),
        phoneNumber: phoneNumber,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

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
      await Future.delayed(const Duration(seconds: 1));
      return true;
    } catch (e) {
      throw Exception('Student verification failed: $e');
    }
  }

  Future<UserModel?> getUser(String userId) async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      return null;
    } catch (e) {
      throw Exception('Get user failed: $e');
    }
  }

  Future<void> updateUser(UserModel user) async {
    try {
      await Future.delayed(const Duration(milliseconds: 500));
    } catch (e) {
      throw Exception('Update user failed: $e');
    }
  }
}
