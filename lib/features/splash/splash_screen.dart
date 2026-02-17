import 'package:flutter/cupertino.dart';
import '../../router/route_names.dart';

/// 스플래시 화면 → 약관(terms) 또는 메인으로 전환
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigateToNext();
  }

  Future<void> _navigateToNext() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;
    // 더미: 로그인 없이 약관 → 온보딩 흐름으로 이동
    Navigator.of(context).pushReplacementNamed(RouteNames.terms);
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '설레연',
              style: TextStyle(
                fontSize: 36,
                fontWeight: FontWeight.bold,
                color: Color(0xFFFF6B8A),
              ),
            ),
            const SizedBox(height: 16),
            const CupertinoActivityIndicator(color: Color(0xFFFF6B8A)),
          ],
        ),
      ),
    );
  }
}
