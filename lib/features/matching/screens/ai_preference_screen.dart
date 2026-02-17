import 'package:flutter/material.dart';

/// AI 취향 알려주기 화면
class AiPreferenceScreen extends StatelessWidget {
  const AiPreferenceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI에게 내 취향 알려주기')),
      body: const Center(child: Text('AI 취향 분석 화면')),
    );
  }
}
