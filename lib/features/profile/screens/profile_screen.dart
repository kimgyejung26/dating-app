import 'package:flutter/material.dart';

/// 내페이지탭 - 프로필 메인 화면
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('내 페이지')),
      body: const Center(child: Text('프로필 메인 화면')),
    );
  }
}
