import 'package:flutter/material.dart';

/// 상대 그룹 프로필 화면
class GroupProfileScreen extends StatelessWidget {
  const GroupProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('상대 그룹')),
      body: const Center(child: Text('상대 그룹 프로필 화면')),
    );
  }
}
