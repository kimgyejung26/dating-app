import 'package:flutter/material.dart';

/// 학과/계열 선택 화면
class DepartmentScreen extends StatelessWidget {
  const DepartmentScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('학과 선택')),
      body: const Center(child: Text('학과/계열 선택 화면')),
    );
  }
}
