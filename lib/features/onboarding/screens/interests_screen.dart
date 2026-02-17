import 'package:flutter/material.dart';

/// 관심사 선택 화면
class InterestsScreen extends StatelessWidget {
  const InterestsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('관심사')),
      body: const Center(child: Text('관심사 선택 화면')),
    );
  }
}
