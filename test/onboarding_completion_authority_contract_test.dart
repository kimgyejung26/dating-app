import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 온보딩 완료(`initialSetupComplete`) 기록 권한 계약.
///
/// deferred-avatar 온보딩에서는 아바타 승인 뒤 마지막 화면만 온보딩을 완료한다.
/// 이상형 저장/건너뛰기 등 어떤 중간 경로도 `initialSetupComplete` 를 세우면
/// 안 된다. 그렇게 되면 재진입 resolver 가 마지막(아바타 선택) 단계를 건너뛴다.
///
/// legacy(이미 완료된 프로필을 사후 확인하는 경로)는 기존 의미를 유지한다.
Directory _repoRoot() {
  var dir = Directory.current;
  for (var i = 0; i < 4; i++) {
    if (File('${dir.path}/pubspec.yaml').existsSync()) return dir;
    dir = dir.parent;
  }
  fail('pubspec.yaml not found from ${Directory.current.path}');
}

String _read(Directory root, String relative) {
  final file = File('${root.path}/$relative');
  expect(file.existsSync(), isTrue, reason: '$relative must exist');
  return file.readAsStringSync();
}

Iterable<File> _dartFiles(Directory dir) {
  return dir
      .listSync(recursive: true)
      .whereType<File>()
      .where((file) => file.path.endsWith('.dart'));
}

/// 완료 기록을 직접 호출해도 되는 legacy 파일. 신규 deferred 흐름이 아니다.
const Set<String> _legacyCompletionCallers = {
  // 이미 필수 항목이 다 있는 legacy 프로필을 사후에 완료 처리한다.
  'lib/services/auth_service.dart',
  // legacy 초기 설정 화면.
  'lib/screens/auth/initial_setup_screen.dart',
  // legacy provider.
  'lib/features/onboarding/providers/onboarding_provider.dart',
  // 정의부.
  'lib/services/user_service.dart',
};

void main() {
  final root = _repoRoot();

  test(
    'save helper completes onboarding only through completeOnboarding()',
    () {
      final source = _read(root, 'lib/services/onboarding_save_helper.dart');
      final privateCalls = RegExp(
        r'await _completeOnboarding\(uid\);',
      ).allMatches(source).length;
      expect(
        privateCalls,
        1,
        reason:
            '_completeOnboarding must be reachable only from '
            'OnboardingSaveHelper.completeOnboarding()',
      );
      expect(
        source,
        contains('static Future<void> completeOnboarding() async'),
      );
      expect(source, isNot(contains('saveIdealPersonalityAndComplete')));
      expect(source, isNot(contains('saveIdealLifestyleAndComplete')));
      // 건너뛰기는 skipped 플래그만 기록한다.
      final skipBody = source.substring(
        source.indexOf('skipIdealType() async'),
      );
      final skipEnd = skipBody.indexOf('\n  }\n');
      expect(
        skipBody.substring(0, skipEnd),
        isNot(contains('_completeOnboarding')),
      );
    },
  );

  test(
    'only the avatar select screen calls OnboardingSaveHelper.completeOnboarding',
    () {
      final callers = <String>[];
      for (final file in _dartFiles(Directory('${root.path}/lib'))) {
        final text = file.readAsStringSync();
        if (text.contains('OnboardingSaveHelper.completeOnboarding')) {
          callers.add(
            file.path
                .replaceFirst(root.path, '')
                .replaceAll('\\', '/')
                .replaceFirst(RegExp(r'^/'), ''),
          );
        }
      }
      expect(callers, [
        'lib/features/onboarding/screens/avatar_select_screen.dart',
      ]);
    },
  );

  test('no non-legacy client path calls UserService.completeOnboarding', () {
    final offenders = <String>[];
    for (final file in _dartFiles(Directory('${root.path}/lib'))) {
      final rel = file.path
          .replaceFirst(root.path, '')
          .replaceAll('\\', '/')
          .replaceFirst(RegExp(r'^/'), '');
      if (rel == 'lib/services/onboarding_save_helper.dart') continue;
      if (_legacyCompletionCallers.contains(rel)) continue;
      final text = file.readAsStringSync();
      if (RegExp(r'\.completeOnboarding\(').hasMatch(text) &&
          !text.contains('OnboardingSaveHelper.completeOnboarding')) {
        offenders.add(rel);
      }
    }
    expect(offenders, isEmpty);
  });

  test(
    'ideal-type terminal screens route to avatar select, never to tutorial',
    () {
      for (final relative in const [
        'lib/features/onboarding/screens/ideal_type/ideal_type_screen.dart',
        'lib/features/onboarding/screens/ideal_type/ideal_lifestyle_screen.dart',
        'lib/features/onboarding/screens/ideal_type/ideal_personality_screen.dart',
      ]) {
        final source = _read(root, relative);
        expect(
          source,
          isNot(contains('welcomeTutorial')),
          reason: '$relative must not skip the avatar step',
        );
        expect(
          source,
          contains('RouteNames.onboardingAvatarSelect'),
          reason: '$relative must hand off to the avatar select step',
        );
        expect(source, isNot(contains('completeOnboarding')));
      }
    },
  );

  test('avatar select screen completes only after a verified approval', () {
    final source = _read(
      root,
      'lib/features/onboarding/screens/avatar_select_screen.dart',
    );
    final approveIndex = source.indexOf('_client.approveCandidate(');
    final verifyIndex = source.indexOf('!approval.isApproved', approveIndex);
    final finishIndex = source.indexOf(
      'await _finishOnboarding()',
      verifyIndex,
    );
    expect(approveIndex, greaterThan(0));
    expect(verifyIndex, greaterThan(approveIndex));
    expect(finishIndex, greaterThan(verifyIndex));
  });
}
