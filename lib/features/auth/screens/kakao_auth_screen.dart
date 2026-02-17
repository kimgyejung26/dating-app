import 'package:flutter/material.dart';

/// 카카오 인증 화면
class KakaoAuthScreen extends StatelessWidget {
  const KakaoAuthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('카카오톡 인증')),
      body: const Center(child: Text('카카오톡 인증 화면')),
    );
  }
}
