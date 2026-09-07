import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Firebase Hosting exposes the public account-deletion guide', () {
    final firebase =
        jsonDecode(File('firebase.json').readAsStringSync())
            as Map<String, dynamic>;
    final hosting = firebase['hosting'] as Map<String, dynamic>;
    final rewrites = (hosting['rewrites'] as List<dynamic>)
        .cast<Map<String, dynamic>>();

    for (final source in ['/account-deletion', '/account-deletion/**']) {
      expect(
        rewrites.any(
          (rewrite) =>
              rewrite['source'] == source &&
              rewrite['destination'] == '/account-deletion.html',
        ),
        isTrue,
      );
    }

    final index = File('public/index.html').readAsStringSync();
    expect(
      RegExp('href="/account-deletion"').allMatches(index),
      hasLength(greaterThanOrEqualTo(2)),
    );
  });

  test('the public guide and in-app copy agree on retention boundaries', () {
    final guide = File('public/account-deletion.html').readAsStringSync();
    final accountScreen = File(
      'lib/features/profile/screens/account_management_screen.dart',
    ).readAsStringSync();

    expect(guide, contains('support@seolleyeon.com'));
    expect(guide, contains('기본 90일'));
    expect(guide, contains('최대 30일'));
    expect(accountScreen, contains('기본 90일'));
    expect(accountScreen, contains('최대 30일'));
  });
}
