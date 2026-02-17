// 설레연 앱 기본 위젯 테스트

import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/app.dart';

void main() {
  testWidgets('App launches successfully', (WidgetTester tester) async {
    // 앱 빌드 및 프레임 트리거
    await tester.pumpWidget(const SeolleyeonApp());

    // 앱이 정상적으로 로드되는지 확인
    expect(find.text('설레연'), findsOneWidget);
  });
}
