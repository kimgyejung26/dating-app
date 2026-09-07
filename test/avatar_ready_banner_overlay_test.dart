import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_generation_session_controller.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_resume_policy.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_models.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_ready_banner_overlay.dart';
import 'package:seolleyeon/router/route_names.dart';
import 'package:seolleyeon/services/avatar_generation_client.dart';

class _SilentClient extends AvatarGenerationClient {
  @override
  Future<AvatarGenerationStatusSnapshot?> getCurrentGenerationStatus() async =>
      null;

  @override
  Future<AvatarCandidatesResult> getCandidates(String jobId) async =>
      throw UnimplementedError();

  @override
  Future<AvatarApprovalResult> approveCandidate(String candidateId) async =>
      throw UnimplementedError();
}

AvatarGenerationStatusSnapshot _previewSafe({
  String jobId = 'avatar_job_banner_0001',
}) {
  return AvatarGenerationStatusSnapshot.fromMap({
    'sourceLocked': true,
    'jobId': jobId,
    'sourceSelectionVersion': 1,
    'status': 'preview_ready',
    'candidateAvailability': 'preview_safe',
    'retryAllowed': false,
    'approved': false,
  });
}

AvatarGenerationStatusSnapshot _queued({
  String jobId = 'avatar_job_banner_0001',
  bool sourceLocked = true,
}) {
  return AvatarGenerationStatusSnapshot.fromMap({
    'sourceLocked': sourceLocked,
    'jobId': jobId,
    'sourceSelectionVersion': 1,
    'status': 'queued',
    'candidateAvailability': 'none',
    'retryAllowed': false,
    'approved': false,
  });
}

class _Harness {
  _Harness() {
    controller = AvatarGenerationSessionController(
      client: _SilentClient(),
      uidResolver: () async => null,
      profileStreamFactory: (_) => const Stream.empty(),
      authUidStream: const Stream.empty(),
    );
  }

  late final AvatarGenerationSessionController controller;
  final ValueNotifier<String?> route = ValueNotifier<String?>(null);

  Widget build() {
    return MaterialApp(
      home: AvatarReadyBannerOverlay(
        controller: controller,
        currentRouteName: route,
        child: const Scaffold(body: Text('screen')),
      ),
    );
  }

  bool _disposed = false;

  void dispose() {
    if (_disposed) return;
    _disposed = true;
    controller.dispose();
    route.dispose();
  }
}

/// 위젯을 내리고 컨트롤러를 정리한다. 폴링 타이머가 남으면 테스트가 실패한다.
Future<void> _finish(WidgetTester tester, _Harness h) async {
  await tester.pumpWidget(const SizedBox.shrink());
  h.dispose();
}

Finder _banner() => find.byKey(const ValueKey('avatar_ready_banner'));

bool _bannerVisible(WidgetTester tester) {
  if (_banner().evaluate().isEmpty) return false;
  final opacity = tester.widget<AnimatedOpacity>(
    find.ancestor(of: _banner(), matching: find.byType(AnimatedOpacity)),
  );
  return opacity.opacity == 1;
}

Future<void> _settle(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
}

void _setLifecycle(WidgetTester tester, AppLifecycleState state) {
  tester.binding.handleAppLifecycleStateChanged(state);
}

void main() {
  tearDown(() {
    // 다른 테스트로 background 상태가 새지 않게 한다.
    TestWidgetsFlutterBinding.instance.handleAppLifecycleStateChanged(
      AppLifecycleState.resumed,
    );
  });

  testWidgets('shows the banner for 3 seconds in the middle of onboarding', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingSelfIntro;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);

    expect(find.text(avatarReadyBannerTitle), findsOneWidget);
    expect(find.text(avatarReadyBannerBody), findsOneWidget);
    expect(_bannerVisible(tester), isTrue);
    expect(h.controller.bannerShown, isTrue);
    expect(h.controller.completionBannerPending, isFalse);

    await tester.pump(const Duration(seconds: 3));
    await tester.pump(const Duration(milliseconds: 300));
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('every onboarding step except avatar-select shows the banner', (
    tester,
  ) async {
    for (final route in RouteNames.onboardingStepRoutes) {
      if (route == RouteNames.onboardingAvatarSelect) continue;
      final h = _Harness();
      await tester.pumpWidget(h.build());
      h.route.value = route;
      await tester.pump();

      h.controller.applySnapshot(_previewSafe());
      await _settle(tester);
      expect(_bannerVisible(tester), isTrue, reason: '$route must show');

      await tester.pump(const Duration(seconds: 4));
      await _finish(tester, h);
    }
  });

  testWidgets('non-onboarding routes never show the banner', (tester) async {
    for (final route in <String?>[
      RouteNames.main,
      RouteNames.login,
      RouteNames.terms,
      RouteNames.studentVerification,
      RouteNames.kakaoFriendConnect,
      RouteNames.profile,
      RouteNames.myPage,
      RouteNames.community,
      RouteNames.chat,
      RouteNames.welcomeTutorial,
      RouteNames.splash,
      // `/onboarding/` prefix 지만 신규 온보딩이 아닌 보수 라우트.
      RouteNames.campusLifeZoneRepair,
      null,
    ]) {
      final h = _Harness();
      await tester.pumpWidget(h.build());
      h.route.value = route;
      await tester.pump();

      h.controller.applySnapshot(_previewSafe());
      await _settle(tester);
      expect(_bannerVisible(tester), isFalse, reason: '$route must not show');
      expect(
        h.controller.completionBannerPending,
        isTrue,
        reason: '$route must not consume the banner',
      );
      await _finish(tester, h);
    }
  });

  testWidgets('on the avatar select screen the banner is consumed silently', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingAvatarSelect;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);

    expect(_bannerVisible(tester), isFalse);
    expect(h.controller.bannerShown, isTrue);
    expect(h.controller.completionBannerPending, isFalse);
    await _finish(tester, h);
  });

  testWidgets('outside onboarding the banner waits until onboarding resumes', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.main;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await tester.pump();
    expect(_bannerVisible(tester), isFalse);
    expect(h.controller.completionBannerPending, isTrue);

    h.route.value = RouteNames.onboardingKeywords;
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);

    await tester.pump(const Duration(seconds: 4));
    await _finish(tester, h);
  });

  testWidgets('the banner survives an onboarding → onboarding transition', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingSelfIntro;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);

    await tester.pump(const Duration(seconds: 1));
    h.route.value = RouteNames.onboardingProfileQa;
    await tester.pump();
    expect(_bannerVisible(tester), isTrue, reason: '화면 전환에도 유지된다');

    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(milliseconds: 300));
    expect(_bannerVisible(tester), isFalse, reason: '총 3초 뒤에 내려간다');
    await _finish(tester, h);
  });

  testWidgets('entering avatar-select while visible hides the banner at once', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingIdealPersonality;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);

    await tester.pump(const Duration(seconds: 1));
    h.route.value = RouteNames.onboardingAvatarSelect;
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    expect(h.controller.bannerShown, isTrue);

    // 남아 있던 3초 타이머가 다시 켜지지 않는다.
    await tester.pump(const Duration(seconds: 3));
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('the banner is shown at most once per job', (tester) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingProfileQa;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await tester.pump();
    await tester.pump(const Duration(seconds: 4));
    expect(_bannerVisible(tester), isFalse);

    h.controller.applySnapshot(_queued());
    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('a new job shows the banner exactly once more', (tester) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingKeywords;
    await tester.pump();

    h.controller.applySnapshot(_previewSafe(jobId: 'avatar_job_aaaaaaaa'));
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);
    await tester.pump(const Duration(seconds: 4));
    expect(_bannerVisible(tester), isFalse);

    // replace → 새 job.
    h.controller.applySnapshot(_queued(sourceLocked: false));
    h.controller.applySnapshot(_queued(jobId: 'avatar_job_bbbbbbbb'));
    await tester.pump();
    expect(_bannerVisible(tester), isFalse);

    h.controller.applySnapshot(_previewSafe(jobId: 'avatar_job_bbbbbbbb'));
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);
    await tester.pump(const Duration(seconds: 4));
    expect(_bannerVisible(tester), isFalse);

    h.controller.applySnapshot(_queued(jobId: 'avatar_job_bbbbbbbb'));
    h.controller.applySnapshot(_previewSafe(jobId: 'avatar_job_bbbbbbbb'));
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('generation finishing in the background waits for foreground', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingSelfIntro;
    await tester.pump();

    for (final state in const [
      AppLifecycleState.inactive,
      AppLifecycleState.paused,
      AppLifecycleState.detached,
    ]) {
      _setLifecycle(tester, state);
      await tester.pump();
    }

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    expect(h.controller.completionBannerPending, isTrue);
    expect(h.controller.bannerShown, isFalse);

    // 3초가 background 에서 소비되지 않는다.
    await tester.pump(const Duration(seconds: 5));
    expect(h.controller.completionBannerPending, isTrue);

    _setLifecycle(tester, AppLifecycleState.resumed);
    await _settle(tester);
    expect(_bannerVisible(tester), isTrue);
    expect(h.controller.bannerShown, isTrue);

    await tester.pump(const Duration(seconds: 3));
    await tester.pump(const Duration(milliseconds: 300));
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('background completion on avatar-select is consumed silently', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    h.route.value = RouteNames.onboardingAvatarSelect;
    await tester.pump();
    _setLifecycle(tester, AppLifecycleState.paused);
    await tester.pump();

    h.controller.applySnapshot(_previewSafe());
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    expect(h.controller.bannerShown, isTrue);

    _setLifecycle(tester, AppLifecycleState.resumed);
    await _settle(tester);
    expect(_bannerVisible(tester), isFalse);
    await _finish(tester, h);
  });

  testWidgets('entering onboarding starts the session, leaving stops it', (
    tester,
  ) async {
    final h = _Harness();
    await tester.pumpWidget(h.build());
    expect(h.controller.isStarted, isFalse);

    h.route.value = RouteNames.onboardingBasicInfo;
    await tester.pump();
    expect(h.controller.isStarted, isTrue);

    h.route.value = RouteNames.welcomeTutorial;
    await tester.pump();
    expect(h.controller.isStarted, isFalse);

    // 보수 라우트는 온보딩이 아니므로 세션을 시작하지 않는다.
    h.route.value = RouteNames.campusLifeZoneRepair;
    await tester.pump();
    expect(h.controller.isStarted, isFalse);
    await _finish(tester, h);
  });
}
