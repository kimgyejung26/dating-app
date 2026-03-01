import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import '../../providers/auth_provider.dart';

class KakaoCallbackScreen extends StatefulWidget {
  const KakaoCallbackScreen({super.key});

  @override
  State<KakaoCallbackScreen> createState() => _KakaoCallbackScreenState();
}

class _KakaoCallbackScreenState extends State<KakaoCallbackScreen> {
  String _statusMessage = '로그인 처리 중...';
  bool _handled = false;

  @override
  void initState() {
    super.initState();
    _handleCallback();
  }

  Future<void> _handleCallback() async {
    if (_handled) return;
    _handled = true;

    final uri = Uri.base;
    final query = uri.queryParameters;
    final error = query['error'];
    final errorDescription = query['error_description'];

    // 1) 카카오에서 에러로 리다이렉트된 경우
    if (error != null) {
      setState(() {
        _statusMessage = '로그인 실패: ${errorDescription ?? error}';
      });
      if (mounted) context.go('/login');
      return;
    }

    // 2) 여기서 code가 있어도(redirect flow),
    //    지금은 서버에서 code->token 교환을 구현하지 않았으므로
    //    "SDK에 이미 세션/토큰이 있다"는 전제 하에 me()를 시도해본다.
    try {
      setState(() => _statusMessage = '카카오 사용자 정보 확인 중...');

      final user = await UserApi.instance.me();
      final kakaoUserId = user.id.toString();

      final userInfo = {
        'id': kakaoUserId,
        'nickname': user.kakaoAccount?.profile?.nickname,
        'profileImageUrl': user.kakaoAccount?.profile?.profileImageUrl,
        'email': user.kakaoAccount?.email,
      };

      // 3) 여기서 "로그인 상태"를 진짜로 true로 만든다 (라우터 redirect가 여기 보고 판단함)
      final authProvider = context.read<AuthProvider>();
      await authProvider.setKakaoLogin(kakaoUserId, userInfo: userInfo);

      if (!mounted) return;
      setState(() => _statusMessage = '로그인 완료! 이동 중...');

      if (!authProvider.isStudentVerified) {
        context.go('/student-verification');
      } else if (!authProvider.isInitialSetupComplete) {
        context.go('/initial-setup');
      } else {
        context.go('/home');
      }
    } on KakaoException catch (e) {
      final detail = e.message ?? e.toString();
      setState(() => _statusMessage = '카카오 로그인 실패: $detail');

      if (mounted) context.go('/login');
    } catch (e) {
      setState(() => _statusMessage = '로그인 처리 실패: $e');
      if (mounted) context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('카카오 로그인 콜백')),
      body: Center(
        child: Text(_statusMessage, style: const TextStyle(fontSize: 16)),
      ),
    );
  }
}
