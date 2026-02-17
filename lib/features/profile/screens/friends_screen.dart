import 'package:flutter/material.dart';

/// 친구 목록 화면
class FriendsScreen extends StatelessWidget {
  const FriendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('친구')),
      body: const Center(child: Text('친구 목록 화면')),
    );
  }
}
