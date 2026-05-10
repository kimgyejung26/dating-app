import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:stamp_animation/features/stamp_3d/real_3d_stamp_page.dart';

void main() {
  testWidgets('3D stamp page starts with disabled loading button', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Real3DStampPage(
          modelViewerBuilder: (_) => const SizedBox.expand(),
        ),
      ),
    );

    expect(find.text('3D 모델 로딩 중...'), findsWidgets);
    expect(
      tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
      isNull,
    );
  });
}
