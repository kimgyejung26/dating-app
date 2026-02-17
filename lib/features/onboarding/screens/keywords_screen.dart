import 'package:flutter/material.dart';

/// 나를 표현하는 키워드 선택 화면
class KeywordsScreen extends StatelessWidget {
  const KeywordsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('나를 표현하는 키워드')),
      body: const Center(child: Text('키워드 선택 화면')),
    );
  }
}
