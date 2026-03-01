import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../../router/route_names.dart';
import '../../../services/auth_service.dart';
import '../../../services/storage_service.dart';

/// 카카오 인증 화면
class KakaoAuthScreen extends StatefulWidget {
  const KakaoAuthScreen({super.key});

  @override
  State<KakaoAuthScreen> createState() => _KakaoAuthScreenState();
}

class _KakaoAuthScreenState extends State<KakaoAuthScreen> {
  final _authService = AuthService();
  final _storageService = StorageService();

  bool _isLoading = false;
  String? _errorMessage;

  Future<void> _login() async {
    if (_isLoading) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final userInfo = await _authService.loginWithKakao();
      final kakaoUserId = userInfo['id']?.toString();

      if (kakaoUserId == null || kakaoUserId.isEmpty) {
        throw Exception('카카오 사용자 ID를 가져오지 못했습니다.');
      }

      await _storageService.saveKakaoUserId(kakaoUserId);

      if (!mounted) return;
      // ✅ 이미 서버에 등록 + 초기설정/튜토리얼까지 완료된 유저면 홈으로 바로 이동
      final exists = await _authService.kakaoUserExists(kakaoUserId);
      if (exists) {
        final isVerified = await _authService.isStudentVerified(kakaoUserId);
        final isInitialSetupComplete = await _authService.isInitialSetupComplete(
          kakaoUserId,
        );
        final hasSeenTutorial = await _authService.hasSeenTutorial(kakaoUserId);

        if (isVerified && isInitialSetupComplete && hasSeenTutorial) {
          if (!mounted) return;
          Navigator.of(context).pushNamedAndRemoveUntil(
            RouteNames.main,
            (route) => false,
          );
          return;
        }

        if (!mounted) return;
        if (!isVerified) {
          Navigator.of(context).pushReplacementNamed(
            RouteNames.studentVerification,
          );
          return;
        }
        if (!isInitialSetupComplete) {
          Navigator.of(context).pushReplacementNamed(
            RouteNames.onboardingBasicInfo,
          );
          return;
        }
        if (!hasSeenTutorial) {
          Navigator.of(context).pushReplacementNamed(
            RouteNames.welcomeTutorial,
          );
          return;
        }
      }

      // 신규/미완료 유저 기본 플로우
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed(
        RouteNames.studentVerification,
      );
    } catch (e) {
      final msg = e.toString().replaceFirst('Exception: ', '');
      setState(() => _errorMessage = msg);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      navigationBar: const CupertinoNavigationBar(
        middle: Text('카카오 로그인'),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              const Text(
                '카카오로 시작하기',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                '카카오 계정으로 로그인하면\n바로 프로필 설정을 진행할 수 있어요.',
                style: TextStyle(
                  fontSize: 15,
                  height: 1.4,
                  color: Color(0xFF64748B),
                ),
              ),
              const SizedBox(height: 18),
              if (_errorMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE8EA),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFFC2CC)),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(
                      fontSize: 13,
                      color: Color(0xFFB42318),
                      height: 1.35,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],
              const Spacer(),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: CupertinoButton(
                  padding: EdgeInsets.zero,
                  borderRadius: BorderRadius.circular(28),
                  color: const Color(0xFFFF6B8A),
                  onPressed: _isLoading ? null : _login,
                  child: _isLoading
                      ? const CupertinoActivityIndicator(color: Colors.white)
                      : const Text(
                          '카카오로 로그인',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 10),
              Center(
                child: CupertinoButton(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  onPressed: _isLoading
                      ? null
                      : () => Navigator.of(context).pushReplacementNamed(
                            RouteNames.terms,
                          ),
                  child: const Text(
                    '약관으로 돌아가기',
                    style: TextStyle(
                      fontSize: 14,
                      color: Color(0xFF64748B),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
