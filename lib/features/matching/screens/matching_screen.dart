import 'package:flutter/material.dart';

/// 설레연탭 - 1:1 매칭 메인 화면
class MatchingScreen extends StatelessWidget {
  const MatchingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설레연')),
      body: const Center(child: Text('1:1 매칭 화면')),
    );
  }
}
