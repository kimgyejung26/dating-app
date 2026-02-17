import 'package:flutter/material.dart';

/// 3:3 그룹 로비 화면 (인원 구성/대기)
class GroupLobbyScreen extends StatelessWidget {
  const GroupLobbyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('인원 구성')),
      body: const Center(child: Text('그룹 로비 화면')),
    );
  }
}
