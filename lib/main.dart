import 'package:flutter/material.dart';

import 'features/stamp_3d/real_3d_stamp_page.dart';

void main() {
  runApp(const StampAnimationApp());
}

class StampAnimationApp extends StatelessWidget {
  const StampAnimationApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Stamp Animation',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xffb21f2d)),
        useMaterial3: true,
      ),
      home: const Real3DStampPage(),
    );
  }
}
