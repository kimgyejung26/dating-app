import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_generation_session_controller.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_resume_policy.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_models.dart';
import 'package:seolleyeon/services/avatar_generation_client.dart';

/// 상태 콜러블만 흉내 내는 클라이언트. 테스트가 [snapshot] 을 바꾸면 다음
/// refresh 부터 그 값을 돌려준다.
class _StatusClient extends AvatarGenerationClient {
  Map<String, dynamic>? snapshot;
  int statusCalls = 0;
  bool throwOnStatus = false;
  Completer<AvatarGenerationStatusSnapshot?>? pendingStatus;

  @override
  Future<AvatarGenerationStatusSnapshot?> getCurrentGenerationStatus() async {
    statusCalls += 1;
    final pending = pendingStatus;
    if (pending != null) return pending.future;
    if (throwOnStatus) throw Exception('network');
    final current = snapshot;
    if (current == null) return null;
    return AvatarGenerationStatusSnapshot.fromMap(
      Map<String, dynamic>.from(current),
    );
  }

  @override
  Future<AvatarCandidatesResult> getCandidates(String jobId) async =>
      throw UnimplementedError();

  @override
  Future<AvatarApprovalResult> approveCandidate(String candidateId) async =>
      throw UnimplementedError();
}

Map<String, dynamic> _snap(
  String status, {
  String candidateAvailability = 'none',
  bool sourceLocked = true,
  bool retryAllowed = false,
  bool approved = false,
  String jobId = 'avatar_job_session_0001',
}) {
  return {
    'sourceLocked': sourceLocked,
    'jobId': jobId,
    'sourceSelectionVersion': 1,
    'status': status,
    'candidateAvailability': candidateAvailability,
    'retryAllowed': retryAllowed,
    'approved': approved,
    'safeReasonCode': null,
  };
}

AvatarGenerationStatusSnapshot _snapshot(
  String status, {
  String candidateAvailability = 'none',
  bool sourceLocked = true,
  bool retryAllowed = false,
  bool approved = false,
  String jobId = 'avatar_job_session_0001',
}) {
  return AvatarGenerationStatusSnapshot.fromMap(
    _snap(
      status,
      candidateAvailability: candidateAvailability,
      sourceLocked: sourceLocked,
      retryAllowed: retryAllowed,
      approved: approved,
      jobId: jobId,
    ),
  );
}

AvatarGenerationStatusSnapshot _previewSafe({
  String jobId = 'avatar_job_session_0001',
}) => _snapshot(
  'preview_ready',
  candidateAvailability: 'preview_safe',
  jobId: jobId,
);

Map<String, dynamic> _profile({
  String? status,
  String? jobId,
  String? approvedUrl,
}) {
  return {
    'avatar': {
      if (status != null) 'status': status,
      if (approvedUrl != null) 'approvedAvatarUrl': approvedUrl,
    },
    'onboarding': {if (jobId != null) 'avatarGenerationJobId': jobId},
  };
}

class _Harness {
  _Harness({Duration? fallback, Duration? safety}) {
    controller = AvatarGenerationSessionController(
      client: client,
      uidResolver: () async => uid,
      profileStreamFactory: (requestedUid) {
        subscribedUids.add(requestedUid);
        return profile.stream;
      },
      authUidStream: auth.stream,
      fallbackPollInterval: fallback ?? const Duration(seconds: 5),
      safetyPollInterval: safety ?? const Duration(seconds: 20),
    );
  }

  final _StatusClient client = _StatusClient();
  final StreamController<Map<String, dynamic>?> profile =
      StreamController<Map<String, dynamic>?>.broadcast();
  final StreamController<String?> auth = StreamController<String?>.broadcast();
  final List<String> subscribedUids = <String>[];
  String? uid = 'uid_session_1';
  late final AvatarGenerationSessionController controller;

  bool _closed = false;

  /// 위젯 테스트는 본문 끝에서 반드시 호출한다. 컨트롤러의 폴링 타이머가
  /// 남아 있으면 flutter_test 가 "Timer is still pending" 으로 실패시킨다.
  void close() {
    if (_closed) return;
    _closed = true;
    controller.dispose();
    profile.close();
    auth.close();
  }
}

void main() {
  test('late status response cannot restore a reset user session', () async {
    final client = _StatusClient();
    final controller = AvatarGenerationSessionController(client: client);
    addTearDown(controller.dispose);
    client.pendingStatus = Completer<AvatarGenerationStatusSnapshot?>();
    final oldRefresh = controller.refresh();
    controller.reset();
    client.pendingStatus!.complete(_previewSafe(jobId: 'avatar_job_old_user'));
    await oldRefresh;
    expect(controller.jobId, isEmpty);
    expect(controller.completionBannerPending, isFalse);
    expect(controller.phase, AvatarSessionPhase.idle);
  });

  test('new session refresh proceeds while old response is pending', () async {
    final client = _StatusClient();
    final controller = AvatarGenerationSessionController(client: client);
    addTearDown(controller.dispose);
    final oldResponse = Completer<AvatarGenerationStatusSnapshot?>();
    client.pendingStatus = oldResponse;
    final oldRefresh = controller.refresh();
    controller.reset();
    client.pendingStatus = null;
    client.snapshot = _snap('queued', jobId: 'avatar_job_new_user');
    await controller.refresh();
    expect(controller.jobId, 'avatar_job_new_user');
    oldResponse.complete(_previewSafe(jobId: 'avatar_job_old_user'));
    await oldRefresh;
    expect(controller.jobId, 'avatar_job_new_user');
    expect(controller.phase, AvatarSessionPhase.generating);
    expect(controller.completionBannerPending, isFalse);
  });
  group('applySnapshot state machine', () {
    late AvatarGenerationSessionController controller;

    setUp(() {
      controller = AvatarGenerationSessionController(
        client: _StatusClient(),
        uidResolver: () async => null,
        profileStreamFactory: (_) => const Stream.empty(),
        authUidStream: const Stream.empty(),
      );
    });

    tearDown(() => controller.dispose());

    test('queued → preview_ready(none) → preview_safe → approved', () {
      controller.applySnapshot(_snapshot('queued'));
      expect(controller.phase, AvatarSessionPhase.generating);
      expect(controller.jobId, 'avatar_job_session_0001');
      expect(controller.completionBannerPending, isFalse);

      controller.applySnapshot(_snapshot('preview_ready'));
      expect(
        controller.phase,
        AvatarSessionPhase.generating,
        reason: 'preview_ready 라도 safe 후보가 없으면 계속 기다린다',
      );
      expect(controller.completionBannerPending, isFalse);

      controller.applySnapshot(_previewSafe());
      expect(controller.phase, AvatarSessionPhase.previewReady);
      expect(controller.hasSafeCandidates, isTrue);
      expect(controller.completionBannerPending, isTrue);

      controller.applySnapshot(_snapshot('approved', approved: true));
      expect(controller.phase, AvatarSessionPhase.approved);
      expect(controller.completionBannerPending, isFalse);
    });

    test('completion banner is once-only for the same job', () {
      controller.applySnapshot(_previewSafe());
      expect(controller.completionBannerPending, isTrue);

      controller.markBannerShown();
      expect(controller.completionBannerPending, isFalse);
      expect(controller.bannerShown, isTrue);
      expect(controller.bannerShownForJobId, 'avatar_job_session_0001');

      // 같은 preview_ready 스냅샷이 반복돼도 다시 켜지지 않는다.
      controller.applySnapshot(_previewSafe());
      expect(controller.completionBannerPending, isFalse);

      // 같은 job 이 generating 을 거쳐 다시 preview_ready 가 돼도 한 번뿐이다.
      controller.applySnapshot(_snapshot('queued'));
      controller.applySnapshot(_previewSafe());
      expect(controller.completionBannerPending, isFalse);
    });

    test('a new job re-arms the banner exactly once', () {
      // JOB A: 배너 소비.
      controller.applySnapshot(_previewSafe(jobId: 'avatar_job_aaaaaaaa'));
      expect(controller.completionBannerPending, isTrue);
      controller.markBannerShown();
      expect(controller.bannerShown, isTrue);

      // JOB A 실패 → replace → 새 generation JOB B.
      controller.applySnapshot(
        _snapshot('needs_review', jobId: 'avatar_job_aaaaaaaa'),
      );
      controller.applySnapshot(_snapshot('queued', sourceLocked: false));
      expect(controller.jobId, isEmpty);
      controller.applySnapshot(
        _snapshot('queued', jobId: 'avatar_job_bbbbbbbb'),
      );
      expect(controller.jobId, 'avatar_job_bbbbbbbb');
      expect(controller.bannerShown, isFalse);
      expect(controller.completionBannerPending, isFalse);

      // JOB B preview_ready → 정확히 한 번 더.
      controller.applySnapshot(_previewSafe(jobId: 'avatar_job_bbbbbbbb'));
      expect(controller.completionBannerPending, isTrue);
      controller.markBannerShown();
      expect(controller.bannerShownForJobId, 'avatar_job_bbbbbbbb');

      controller.applySnapshot(
        _snapshot('queued', jobId: 'avatar_job_bbbbbbbb'),
      );
      controller.applySnapshot(_previewSafe(jobId: 'avatar_job_bbbbbbbb'));
      expect(controller.completionBannerPending, isFalse);
    });

    test('job change while already in preview re-arms the banner', () {
      controller.applySnapshot(_previewSafe(jobId: 'avatar_job_aaaaaaaa'));
      controller.markBannerShown();

      // 서버가 곧바로 다른 job 의 preview_ready 를 알린 경우(재시도 직후).
      controller.applySnapshot(_previewSafe(jobId: 'avatar_job_bbbbbbbb'));
      expect(controller.jobId, 'avatar_job_bbbbbbbb');
      expect(controller.completionBannerPending, isTrue);
    });

    test('attention states carry the resume policy flags', () {
      controller.applySnapshot(_snapshot('needs_review'));
      expect(controller.phase, AvatarSessionPhase.attention);
      expect(controller.plan?.action, AvatarResumeAction.showNeedsReview);
      expect(controller.plan?.retryAllowed, isFalse);
      expect(controller.plan?.allowsNewGeneration, isTrue);

      controller.applySnapshot(
        _snapshot('retryable_failed', retryAllowed: true),
      );
      expect(controller.phase, AvatarSessionPhase.attention);
      expect(controller.plan?.retryAllowed, isTrue);

      controller.applySnapshot(_snapshot('no_previewable_candidates'));
      expect(controller.plan?.action, AvatarResumeAction.showRetryable);
      expect(controller.plan?.allowsNewGeneration, isTrue);

      controller.applySnapshot(_snapshot('terminal_failed'));
      expect(controller.plan?.action, AvatarResumeAction.showTerminal);
      expect(controller.plan?.allowsNewGeneration, isTrue);

      controller.applySnapshot(_snapshot('reconciliation_required'));
      expect(controller.plan?.action, AvatarResumeAction.showReconciliation);
      expect(controller.plan?.retryAllowed, isFalse);
      expect(controller.plan?.allowsNewGeneration, isFalse);
    });

    test('a pending banner is dropped when the job leaves preview_ready', () {
      controller.applySnapshot(_previewSafe());
      expect(controller.completionBannerPending, isTrue);

      controller.applySnapshot(_snapshot('needs_review'));
      expect(controller.completionBannerPending, isFalse);
      expect(controller.bannerShown, isFalse);
    });

    test('unlocked server state clears the job', () {
      controller.applySnapshot(_snapshot('queued'));
      controller.applySnapshot(_snapshot('queued', sourceLocked: false));
      expect(controller.phase, AvatarSessionPhase.idle);
      expect(controller.jobId, isEmpty);
    });

    test('unreadable status only becomes unavailable before any snapshot', () {
      controller.applySnapshot(null);
      expect(controller.phase, AvatarSessionPhase.unavailable);

      controller.applySnapshot(_snapshot('queued'));
      expect(controller.phase, AvatarSessionPhase.generating);

      controller.applySnapshot(null);
      expect(
        controller.phase,
        AvatarSessionPhase.generating,
        reason: '일시적 조회 실패로 아는 상태를 버리지 않는다',
      );
    });
  });

  group('profile change key', () {
    test('changes only on status / jobId / approved url', () {
      final base = AvatarGenerationSessionController.profileChangeKey(
        _profile(status: 'queued', jobId: 'avatar_job_a'),
      );
      expect(
        AvatarGenerationSessionController.profileChangeKey(
          _profile(status: 'queued', jobId: 'avatar_job_a'),
        ),
        base,
      );
      expect(
        AvatarGenerationSessionController.profileChangeKey(
          _profile(status: 'preview_ready', jobId: 'avatar_job_a'),
        ),
        isNot(base),
      );
      expect(
        AvatarGenerationSessionController.profileChangeKey(
          _profile(
            status: 'queued',
            jobId: 'avatar_job_a',
            approvedUrl: 'https://cdn.example/a.png',
          ),
        ),
        isNot(base),
      );
      expect(
        AvatarGenerationSessionController.profileChangeKey(null),
        '<missing>',
      );
    });
  });

  group('listener, polling and auth', () {
    testWidgets('adoptJob switches to generating and confirms with server', (
      tester,
    ) async {
      final h = _Harness();
      h.client.snapshot = _snap('source_selecting');

      final adopt = h.controller.adoptJob('avatar_job_adopted_1');
      expect(h.controller.phase, AvatarSessionPhase.generating);
      expect(h.controller.jobId, 'avatar_job_adopted_1');
      await adopt;

      expect(h.controller.isStarted, isTrue);
      expect(h.client.statusCalls, greaterThanOrEqualTo(1));
      expect(h.controller.jobId, 'avatar_job_session_0001');
      expect(h.controller.phase, AvatarSessionPhase.generating);
      h.close();
    });

    testWidgets('profile listener change triggers a server refresh', (
      tester,
    ) async {
      final h = _Harness();
      h.client.snapshot = _snap('queued');

      await h.controller.ensureStarted();
      final initialCalls = h.client.statusCalls;
      expect(initialCalls, greaterThanOrEqualTo(1));
      expect(h.controller.listenerHealthy, isTrue);
      expect(h.subscribedUids, ['uid_session_1']);

      h.profile.add(_profile(status: 'queued', jobId: 'avatar_job_x'));
      await tester.pump();
      final afterFirst = h.client.statusCalls;
      expect(afterFirst, greaterThan(initialCalls));

      // 같은 값이면 다시 읽지 않는다.
      h.profile.add(_profile(status: 'queued', jobId: 'avatar_job_x'));
      await tester.pump();
      expect(h.client.statusCalls, afterFirst);

      // 상태가 바뀌면 콜러블로 확정한다(사용자 문서만으로 결정하지 않는다).
      h.client.snapshot = _snap(
        'preview_ready',
        candidateAvailability: 'preview_safe',
      );
      h.profile.add(_profile(status: 'preview_ready', jobId: 'avatar_job_x'));
      await tester.pump();
      expect(h.client.statusCalls, greaterThan(afterFirst));
      expect(h.controller.phase, AvatarSessionPhase.previewReady);
      expect(h.controller.completionBannerPending, isTrue);
      h.close();
    });

    testWidgets(
      'users doc preview_ready is only a trigger: callable decides safety',
      (tester) async {
        final h = _Harness();
        h.client.snapshot = _snap('queued');
        await h.controller.ensureStarted();

        // 문서는 preview_ready 라고 하지만 콜러블은 safe 후보 없음.
        h.client.snapshot = _snap('preview_ready');
        h.profile.add(_profile(status: 'preview_ready', jobId: 'avatar_job_x'));
        await tester.pump();

        expect(h.controller.phase, AvatarSessionPhase.generating);
        expect(h.controller.completionBannerPending, isFalse);
        h.close();
      },
    );

    testWidgets('listener error falls back to short-interval polling', (
      tester,
    ) async {
      final h = _Harness(
        fallback: const Duration(seconds: 2),
        safety: const Duration(minutes: 5),
      );
      h.client.snapshot = _snap('queued');

      await h.controller.ensureStarted();
      final before = h.client.statusCalls;

      h.profile.addError(Exception('permission-denied'));
      await tester.pump();
      expect(h.controller.listenerHealthy, isFalse);

      await tester.pump(const Duration(seconds: 2));
      await tester.pump(const Duration(seconds: 2));
      expect(h.client.statusCalls, greaterThan(before));
      h.close();
    });

    testWidgets(
      'healthy listener still runs the slow safety poll while generating',
      (tester) async {
        final h = _Harness(
          fallback: const Duration(seconds: 1),
          safety: const Duration(seconds: 10),
        );
        h.client.snapshot = _snap('queued');

        await h.controller.ensureStarted();
        final before = h.client.statusCalls;

        await tester.pump(const Duration(seconds: 5));
        expect(h.client.statusCalls, before, reason: 'fallback 간격은 쓰지 않는다');

        await tester.pump(const Duration(seconds: 10));
        expect(h.client.statusCalls, before + 1);
        h.close();
      },
    );

    testWidgets(
      'repeated starts and adoptions never create a second poll loop',
      (tester) async {
        final h = _Harness(
          fallback: const Duration(seconds: 1),
          safety: const Duration(seconds: 10),
        );
        h.client.snapshot = _snap('queued');

        await h.controller.ensureStarted();
        await h.controller.ensureStarted();
        await h.controller.adoptJob('avatar_job_session_0001');
        await h.controller.adoptJob('avatar_job_session_0001');
        await h.controller.refresh();
        final before = h.client.statusCalls;

        await tester.pump(const Duration(seconds: 30));
        expect(
          h.client.statusCalls,
          before + 3,
          reason: '10초 간격 타이머 하나만 돌아야 한다',
        );
        h.close();
      },
    );

    testWidgets('polling stops once candidates are ready', (tester) async {
      final h = _Harness(
        fallback: const Duration(seconds: 1),
        safety: const Duration(seconds: 1),
      );
      h.client.snapshot = _snap(
        'preview_ready',
        candidateAvailability: 'preview_safe',
      );

      await h.controller.ensureStarted();
      expect(h.controller.phase, AvatarSessionPhase.previewReady);
      expect(h.controller.hasPollTimer, isFalse);
      final before = h.client.statusCalls;

      await tester.pump(const Duration(seconds: 5));
      expect(h.client.statusCalls, before);
      h.close();
    });

    testWidgets('polling stops on terminal attention states', (tester) async {
      final h = _Harness(
        fallback: const Duration(seconds: 1),
        safety: const Duration(seconds: 1),
      );
      h.client.snapshot = _snap('queued');
      await h.controller.ensureStarted();
      expect(h.controller.hasPollTimer, isTrue);

      h.client.snapshot = _snap('terminal_failed');
      await h.controller.refresh();
      expect(h.controller.phase, AvatarSessionPhase.attention);
      expect(h.controller.hasPollTimer, isFalse);

      final before = h.client.statusCalls;
      await tester.pump(const Duration(seconds: 5));
      expect(h.client.statusCalls, before);
      h.close();
    });

    testWidgets('auth sign-out resets the session and stops listening', (
      tester,
    ) async {
      final h = _Harness();
      h.client.snapshot = _snap(
        'preview_ready',
        candidateAvailability: 'preview_safe',
      );

      await h.controller.ensureStarted();
      expect(h.controller.phase, AvatarSessionPhase.previewReady);
      expect(h.controller.completionBannerPending, isTrue);
      h.controller.markBannerShown();

      h.auth.add(null);
      await tester.pump();

      expect(h.controller.isStarted, isFalse);
      expect(h.controller.phase, AvatarSessionPhase.idle);
      expect(h.controller.jobId, isEmpty);
      expect(h.controller.plan, isNull);
      expect(h.controller.hasSafeCandidates, isFalse);
      expect(h.controller.bannerShownForJobId, isEmpty);
      expect(h.controller.completionBannerPending, isFalse);
      expect(h.controller.hasPollTimer, isFalse);

      final calls = h.client.statusCalls;
      h.profile.add(_profile(status: 'preview_ready', jobId: 'avatar_job_x'));
      await tester.pump();
      expect(h.client.statusCalls, calls, reason: '리스너가 해제돼야 한다');
      h.close();
    });

    testWidgets(
      'user switch: B starts clean and never sees A\'s job or banner',
      (tester) async {
        final h = _Harness(
          fallback: const Duration(seconds: 1),
          safety: const Duration(seconds: 1),
        );
        // UID A: job A 진행 중, 배너 대기 상태.
        h.uid = 'uid_A';
        h.client.snapshot = _snap(
          'preview_ready',
          candidateAvailability: 'preview_safe',
          jobId: 'avatar_job_aaaaaaaa',
        );
        await h.controller.ensureStarted();
        expect(h.controller.uid, 'uid_A');
        expect(h.controller.jobId, 'avatar_job_aaaaaaaa');
        expect(h.controller.completionBannerPending, isTrue);

        // logout.
        h.auth.add(null);
        await tester.pump();
        expect(h.controller.uid, isEmpty);
        expect(h.controller.jobId, isEmpty);
        expect(h.controller.completionBannerPending, isFalse);
        expect(h.controller.hasPollTimer, isFalse);

        // UID B login: 서버는 B 에게 아직 아무 작업도 없다고 답한다.
        h.uid = 'uid_B';
        h.auth.add('uid_B');
        await tester.pump();
        h.client.snapshot = _snap('queued', sourceLocked: false);
        await h.controller.ensureStarted();

        expect(h.controller.uid, 'uid_B');
        expect(h.subscribedUids.last, 'uid_B');
        expect(h.controller.phase, AvatarSessionPhase.idle);
        expect(h.controller.jobId, isEmpty);
        expect(h.controller.completionBannerPending, isFalse);
        expect(h.controller.bannerShownForJobId, isEmpty);

        // A 의 리스너는 죽었다: A 문서 이벤트가 와도 B 세션은 흔들리지 않는다.
        final calls = h.client.statusCalls;
        await tester.pump(const Duration(seconds: 3));
        expect(h.client.statusCalls, calls);
        h.close();
      },
    );

    testWidgets('uid change in the auth stream resets even while stopped', (
      tester,
    ) async {
      final h = _Harness();
      h.uid = 'uid_A';
      h.client.snapshot = _snap('queued', jobId: 'avatar_job_aaaaaaaa');
      await h.controller.ensureStarted();
      // 온보딩 구간을 벗어나 리스너는 멈췄지만 상태는 남아 있다.
      h.controller.stop();
      expect(h.controller.jobId, 'avatar_job_aaaaaaaa');

      h.auth.add('uid_B');
      await tester.pump();

      expect(h.controller.jobId, isEmpty);
      expect(h.controller.phase, AvatarSessionPhase.idle);
      h.close();
    });

    testWidgets('restart under a different uid clears stale state', (
      tester,
    ) async {
      final h = _Harness();
      h.uid = 'uid_A';
      h.client.snapshot = _snap(
        'preview_ready',
        candidateAvailability: 'preview_safe',
        jobId: 'avatar_job_aaaaaaaa',
      );
      await h.controller.ensureStarted();
      h.controller.stop();
      expect(h.controller.completionBannerPending, isTrue);

      // auth 스트림이 없는 환경이라도 다음 시작 때 uid 가 다르면 비운다.
      h.uid = 'uid_B';
      h.client.snapshot = _snap('queued', sourceLocked: false);
      await h.controller.ensureStarted();

      expect(h.controller.uid, 'uid_B');
      expect(h.controller.jobId, isEmpty);
      expect(h.controller.completionBannerPending, isFalse);
      h.close();
    });

    testWidgets('stop keeps state but ignores further profile events', (
      tester,
    ) async {
      final h = _Harness();
      h.client.snapshot = _snap('queued');

      await h.controller.ensureStarted();
      h.controller.stop();
      expect(h.controller.hasPollTimer, isFalse);
      final calls = h.client.statusCalls;

      h.profile.add(_profile(status: 'preview_ready', jobId: 'avatar_job_x'));
      await tester.pump();
      expect(h.client.statusCalls, calls);
      expect(h.controller.phase, AvatarSessionPhase.generating);
      h.close();
    });

    testWidgets('status callable exception keeps the known phase', (
      tester,
    ) async {
      final h = _Harness();
      h.client.snapshot = _snap('queued');
      await h.controller.ensureStarted();

      h.client.throwOnStatus = true;
      await h.controller.refresh();
      expect(h.controller.phase, AvatarSessionPhase.generating);
      h.close();
    });

    testWidgets('dispose cancels every timer and subscription', (tester) async {
      final h = _Harness(
        fallback: const Duration(seconds: 1),
        safety: const Duration(seconds: 1),
      );
      h.client.snapshot = _snap('queued');
      await h.controller.ensureStarted();
      expect(h.controller.hasPollTimer, isTrue);

      h.close();
      expect(h.profile.hasListener, isFalse);
      expect(h.auth.hasListener, isFalse);
      await tester.pump(const Duration(seconds: 3));
    });
  });
}
