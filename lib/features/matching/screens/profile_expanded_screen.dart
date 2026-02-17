import 'package:flutter/material.dart';

/// 프로필 확대 화면
class ProfileExpandedScreen extends StatelessWidget {
  const ProfileExpandedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('프로필 사진')),
      body: const Center(child: Text('프로필 확대 화면')),
    );
  }
}
