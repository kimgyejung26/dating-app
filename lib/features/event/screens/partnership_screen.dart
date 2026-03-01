import 'package:flutter/material.dart';

/// 제휴 화면
class PartnershipScreen extends StatelessWidget {
  const PartnershipScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('제휴')),
      body: const Center(child: Text('제휴 화면')),
    );
  }
}
