import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:bottom_navigation_bar/app.dart';

void main() {
  testWidgets('renders the glass navigation bar with Home selected first', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    expect(find.byKey(const ValueKey('glass_nav_bar')), findsOneWidget);
    expect(find.byKey(const ValueKey('glass_nav_item_home')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('glass_nav_item_community')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('glass_nav_item_tutorials')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('glass_nav_item_gallery')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('glass_nav_item_profile')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('glass_nav_label_home')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('glass_nav_label_community')),
      findsNothing,
    );
    expect(find.text('Home'), findsWidgets);
  });

  testWidgets('changes selected tab and visible label when tapped', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.byKey(const ValueKey('glass_nav_item_gallery')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('glass_nav_label_home')), findsNothing);
    expect(
      find.byKey(const ValueKey('glass_nav_label_gallery')),
      findsOneWidget,
    );
    expect(find.text('Gallery'), findsWidgets);
  });

  testWidgets('uses the requested color for unselected tab icons', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    final communityIcon = tester.widget<Icon>(
      find.byIcon(Icons.auto_awesome_outlined),
    );

    expect(communityIcon.color, const Color(0xFFFF6B8A));
  });

  testWidgets('uses the requested color for selected tab icons', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    final homeIcon = tester.widget<Icon>(find.byIcon(Icons.home_outlined));

    expect(homeIcon.color, const Color(0xFFFF2456));
  });

  testWidgets('uses translucent white gradient glass background with blur', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    final background = tester.widget<DecoratedBox>(
      find.byKey(const ValueKey('glass_nav_background')),
    );
    final decoration = background.decoration as BoxDecoration;
    final gradient = decoration.gradient as LinearGradient;

    expect(decoration.color, isNull);
    expect(gradient.begin, Alignment.centerLeft);
    expect(gradient.end, Alignment.centerRight);
    expect(gradient.colors, [
      Colors.white.withValues(alpha: .60),
      Colors.white.withValues(alpha: .82),
      Colors.white.withValues(alpha: .78),
      Colors.white.withValues(alpha: .60),
    ]);
    expect(gradient.stops, const [0, .48, .72, 1]);
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('glass_nav_bar')),
        matching: find.byType(BackdropFilter),
      ),
      findsOneWidget,
    );
  });

  testWidgets('uses the original low-alpha grain painter', (tester) async {
    await tester.pumpWidget(const MyApp());

    final grainLayer = tester.widget<CustomPaint>(
      find.byKey(const ValueKey('glass_nav_grain')),
    );
    final painter = grainLayer.painter as dynamic;

    expect(painter.grainAlpha, .028);
  });

  testWidgets('uses photo capsule dock footprint', (tester) async {
    await tester.pumpWidget(const MyApp());

    final navRect = tester.getRect(find.byKey(const ValueKey('glass_nav_bar')));
    final backgroundRect = tester.getRect(
      find.byKey(const ValueKey('glass_nav_background')),
    );

    expect(navRect.height, 72);
    expect(backgroundRect.left, navRect.left + 16);
    expect(backgroundRect.width, navRect.width - 32);
    expect(backgroundRect.height, 60);
    expect(backgroundRect.bottom, navRect.bottom - 12);
  });

  testWidgets('clips the bar as a full capsule', (tester) async {
    await tester.pumpWidget(const MyApp());

    final clip = tester.widget<ClipRRect>(
      find.byKey(const ValueKey('glass_nav_clip')),
    );

    expect(clip.borderRadius, BorderRadius.circular(30));
  });

  testWidgets('drags the active pill to the nearest icon on release', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    final navRect = tester.getRect(find.byKey(const ValueKey('glass_nav_bar')));
    Offset navPoint(double designX) {
      return Offset(
        navRect.left + navRect.width * (designX / 375),
        navRect.top + 30,
      );
    }

    final gesture = await tester.startGesture(navPoint(37));
    await gesture.moveTo(navPoint(262));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('glass_nav_label_home')), findsNothing);
    expect(
      find.byKey(const ValueKey('glass_nav_label_gallery')),
      findsOneWidget,
    );

    final secondGesture = await tester.startGesture(navPoint(262));
    await secondGesture.moveTo(navPoint(110));
    await tester.pump();
    await secondGesture.up();
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('glass_nav_label_community')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('glass_nav_label_gallery')), findsNothing);
  });

  testWidgets('moves the active pill with the finger during drag', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    final navRect = tester.getRect(find.byKey(const ValueKey('glass_nav_bar')));
    Offset navPoint(double designX) {
      return Offset(
        navRect.left + navRect.width * (designX / 375),
        navRect.top + 30,
      );
    }

    final gesture = await tester.startGesture(navPoint(37));
    await gesture.moveTo(navPoint(187));
    await tester.pump();

    final activePill = tester.widget<AnimatedPositioned>(
      find.byKey(const ValueKey('glass_nav_active_pill')),
    );
    final expectedLeft = (navRect.width - 32) * (187 / 375) - 98;

    expect(activePill.left, moreOrLessEquals(expectedLeft, epsilon: .1));

    await gesture.up();
  });

  testWidgets('uses a wide soft active glow footprint', (tester) async {
    await tester.pumpWidget(const MyApp());

    final activePill = tester.widget<AnimatedPositioned>(
      find.byKey(const ValueKey('glass_nav_active_pill')),
    );

    expect(activePill.width, 196);
    expect(activePill.height, 104);
    expect(activePill.width, greaterThan(activePill.height!));
  });

  testWidgets('uses selected item frame spacing inside the capsule', (
    tester,
  ) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.byKey(const ValueKey('glass_nav_item_community')));
    await tester.pumpAndSettle();

    final communityRect = tester.getRect(
      find.byKey(const ValueKey('glass_nav_item_community')),
    );
    final backgroundRect = tester.getRect(
      find.byKey(const ValueKey('glass_nav_background')),
    );
    final scale = backgroundRect.width / 375;

    expect(
      communityRect.left,
      moreOrLessEquals(backgroundRect.left + (66 * scale), epsilon: .1),
    );
    expect(communityRect.width, moreOrLessEquals(90 * scale, epsilon: .1));
  });

  testWidgets('restores layered soft active pill glow', (tester) async {
    await tester.pumpWidget(const MyApp());

    expect(
      find.byKey(const ValueKey('glass_nav_color_ratio_gradient')),
      findsNothing,
    );
  });
}
