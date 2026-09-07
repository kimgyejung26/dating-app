import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_generation_session_controller.dart';
import 'package:seolleyeon/shared/utils/avatar_lock_policy.dart';

/// 서버가 `users/{uid}.avatar.status` 에 기록하는 모든 리터럴이 클라이언트
/// 어휘([userAvatarStatusVocabulary])에 1:1 로 존재해야 한다.
///
/// 어긋나면 세션 컨트롤러/resolver 가 서버 상태를 모르는 값으로 취급해
/// 사용자를 사진 화면으로 되돌리거나 영원히 기다리게 만든다.
Directory _repoRoot() {
  var dir = Directory.current;
  for (var i = 0; i < 4; i++) {
    if (Directory('${dir.path}/functions/src').existsSync()) return dir;
    dir = dir.parent;
  }
  fail('functions/src not found from ${Directory.current.path}');
}

String _read(Directory root, String relative) {
  final file = File('${root.path}/$relative');
  expect(file.existsSync(), isTrue, reason: '$relative must exist');
  return file.readAsStringSync();
}

Set<String> _matches(String source, RegExp pattern) {
  return pattern
      .allMatches(source)
      .map((m) => m.group(1)!.trim().toLowerCase())
      .toSet();
}

void main() {
  final root = _repoRoot();

  test('state-sync terminal mapping statuses are known to the client', () {
    final source = _read(root, 'functions/src/avatarGenerationStateSync.ts');
    final mapped = _matches(source, RegExp(r'avatarStatus:\s*"([a-z_]+)"'));
    expect(mapped, isNotEmpty);
    for (final status in mapped) {
      expect(
        userAvatarStatusVocabulary,
        contains(status),
        reason: 'state-sync writes avatar.status=$status',
      );
    }

    // cancelled/canceled 는 jobStatus 를 그대로 기록한다.
    expect(source, contains('case "cancelled"'));
    expect(userAvatarStatusVocabulary, containsAll(['cancelled', 'canceled']));

    final preservedBlock = RegExp(
      r'PRESERVED_AVATAR_STATUSES\s*=\s*new Set\(\[([^\]]+)\]',
    ).firstMatch(source);
    expect(preservedBlock, isNotNull);
    final preserved = _matches(preservedBlock!.group(1)!, RegExp(r'"([a-z_]+)"'));
    expect(preserved, containsAll(['approved', 'approval_copying']));
    for (final status in preserved) {
      expect(
        userAvatarStatusVocabulary,
        contains(status),
        reason: 'preserved status $status must be known',
      );
    }
  });

  test('admission, approval and replace statuses are known to the client', () {
    final admission = _read(root, 'functions/src/avatarSourceSetAdmission.ts');
    final approval = _read(root, 'functions/src/avatarApproval.ts');
    final recovery = _read(root, 'functions/src/avatarGenerationRecovery.ts');
    final direct = <String>{
      ..._matches(admission, RegExp(r'"avatar\.status":\s*"([a-z_]+)"')),
      ..._matches(approval, RegExp(r'"avatar\.status":\s*"([a-z_]+)"')),
      ..._matches(recovery, RegExp(r'userAvatarStatus:\s*"([a-z_]+)"')),
    };
    expect(direct, containsAll(['queued', 'approval_copying', 'none']));
    for (final status in direct) {
      expect(
        userAvatarStatusVocabulary,
        contains(status),
        reason: 'server writes avatar.status=$status',
      );
    }
  });

  test('client vocabulary partitions cleanly', () {
    // 사진 편집 잠금 어휘는 전부 진행 중 어휘에 포함된다.
    expect(
      userAvatarWorkInProgressStatuses,
      containsAll(sourceLockedAvatarStatuses),
    );
    // 승인/해제는 진행 중이 아니다.
    expect(userAvatarWorkInProgressStatuses, isNot(contains('approved')));
    expect(userAvatarWorkInProgressStatuses, isNot(contains('none')));
    expect(userAvatarStatusVocabulary, containsAll(['approved', 'none']));
  });
}
