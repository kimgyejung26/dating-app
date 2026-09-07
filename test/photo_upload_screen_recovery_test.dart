// needs_review recovery, server-authoritative retry, and source_selecting
// resume for PhotoUploadScreen.
//
// 사진 화면은 더 이상 폴링하지 않으므로 실패 상태는 전부 서버 상태 조회
// (재진입 복구)로 들어온다. 생성 중 상태는 잠금만 걸고 "다음" 을 통과시킨다.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/screens/photo_upload_screen.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_generation_session_controller.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_resume_policy.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_error_banner.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_messages.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_models.dart';
import 'package:seolleyeon/services/avatar_generation_client.dart';
import 'package:seolleyeon/services/avatar_source_photo_service.dart';
import 'package:seolleyeon/shared/utils/avatar_lock_policy.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _RecoveryClient extends AvatarGenerationClient {
  _RecoveryClient({required this.serverStatus, this.serverRetryAllowed = false});

  String serverStatus;
  bool serverRetryAllowed;
  int replaceCalls = 0;
  int retryCalls = 0;
  int statusCalls = 0;

  @override
  Future<AvatarGenerationStatusSnapshot?> getCurrentGenerationStatus() async {
    statusCalls += 1;
    return AvatarGenerationStatusSnapshot.fromMap({
      'sourceLocked': true,
      'jobId': 'avatar_job_recovery_1',
      'sourceSelectionVersion': 1,
      'status': serverStatus,
      'candidateAvailability': 'none',
      'retryAllowed': serverRetryAllowed,
      'approved': false,
      'safeReasonCode': null,
    });
  }

  @override
  Future<AvatarGenerationStatusSnapshot?> retryCurrentGeneration({
    required String clientRequestId,
  }) async {
    retryCalls += 1;
    serverStatus = 'queued';
    serverRetryAllowed = false;
    return getCurrentGenerationStatus();
  }

  @override
  Future<bool> replaceCurrentGeneration({
    required String clientRequestId,
  }) async {
    replaceCalls += 1;
    return true;
  }

  @override
  Future<AvatarCandidatesResult> getCandidates(String jobId) async =>
      throw StateError('photo screen must not poll candidates');

  @override
  Future<AvatarApprovalResult> approveCandidate(String candidateId) async =>
      throw UnimplementedError();
}

Future<void> _useMobileSurface(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(390, 1100);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

/// 사진 화면 테스트용 세션. 테스트 본문 끝에서 [finish] 로 위젯을 내리고
/// 컨트롤러를 정리해야 한다(폴링 타이머가 남으면 flutter_test 가 실패시킨다).
class _Session {
  _Session(AvatarGenerationClient client)
    : controller = AvatarGenerationSessionController(
        client: client,
        uidResolver: () async => null,
        profileStreamFactory: (_) => const Stream.empty(),
        authUidStream: const Stream.empty(),
      ) {
    addTearDown(dispose);
  }

  final AvatarGenerationSessionController controller;
  bool _disposed = false;

  Future<void> finish(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    dispose();
  }

  void dispose() {
    if (_disposed) return;
    _disposed = true;
    controller.dispose();
  }
}

Widget _harness(
  AvatarGenerationClient client, {
  AvatarGenerationSessionController? controller,
  void Function(List<String>)? onNext,
}) {
  return MaterialApp(
    home: PhotoUploadScreen(
      avatarGenerationClient: client,
      avatarSessionController: controller,
      initialPhotosForTesting: [
        AvatarSourcePhotoService.queuedSlotToken('avatar_job_recovery_1'),
        AvatarSourcePhotoService.queuedSlotToken('avatar_job_recovery_1'),
      ],
      onNext: onNext ?? (_) {},
    ),
  );
}

Finder _nextButton() => find.byType(ElevatedButton).last;

Future<void> _settle(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('needs_review recovery', () {
    testWidgets('shows review copy, no retry, and offers start over', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _RecoveryClient(serverStatus: 'needs_review');
      await tester.pumpWidget(_harness(client));
      await _settle(tester);

      expect(find.text(avatarNeedsReviewMessage), findsOneWidget);
      expect(find.text(avatarGenerationFailedMessage), findsNothing);
      expect(find.text(avatarGenericNoPreviewMessage), findsNothing);
      expect(find.text('다시 시도'), findsNothing);
      expect(find.text(avatarStartOverButtonLabel), findsOneWidget);
      // 같은 generation 재시도 금지: 소스는 여전히 잠겨 있다.
      expect(find.byIcon(Icons.close_rounded), findsNothing);
    });

    testWidgets(
      'start over ends the generation server-side and unlocks the screen',
      (tester) async {
        await _useMobileSurface(tester);
        final client = _RecoveryClient(serverStatus: 'needs_review');
        final session = _Session(client);
        final controller = session.controller;
        controller.applySnapshot(await client.getCurrentGenerationStatus());
        expect(controller.phase, AvatarSessionPhase.attention);

        await tester.pumpWidget(_harness(client, controller: controller));
        await _settle(tester);
        expect(find.text(avatarStartOverButtonLabel), findsOneWidget);

        await tester.tap(find.text(avatarStartOverButtonLabel));
        await _settle(tester);

        expect(client.replaceCalls, 1);
        expect(find.byType(AvatarGenerationErrorBanner), findsNothing);
        expect(find.text(sourceLockedAvatarMessage), findsNothing);
        // 잠금이 풀리고 새 사진 세트를 받을 준비가 된 빈 화면.
        expect(find.text('최소 2장 필요'), findsOneWidget);
        expect(controller.phase, AvatarSessionPhase.idle);
        expect(controller.jobId, isEmpty);
        await session.finish(tester);
      },
    );

    testWidgets('double tap on start over releases exactly once', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _RecoveryClient(serverStatus: 'needs_review');
      await tester.pumpWidget(_harness(client));
      await _settle(tester);

      await tester.tap(find.text(avatarStartOverButtonLabel));
      await tester.tap(
        find.text(avatarStartOverButtonLabel),
        warnIfMissed: false,
      );
      await _settle(tester);

      expect(client.replaceCalls, 1);
    });
  });

  group('server-authoritative retry', () {
    testWidgets('retry goes through the server and keeps the lock', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _RecoveryClient(
        serverStatus: 'retryable_failed',
        serverRetryAllowed: true,
      );
      final session = _Session(client);
      final controller = session.controller;
      var advanced = false;
      await tester.pumpWidget(
        _harness(client, controller: controller, onNext: (_) => advanced = true),
      );
      await _settle(tester);
      expect(find.text('다시 시도'), findsOneWidget);

      await tester.tap(find.text('다시 시도'));
      await _settle(tester);

      expect(
        client.retryCalls,
        1,
        reason: 'the server re-dispatches the same job',
      );
      expect(find.byType(AvatarGenerationErrorBanner), findsNothing);
      expect(find.text(sourceLockedAvatarMessage), findsOneWidget);
      expect(controller.jobId, 'avatar_job_recovery_1');
      expect(controller.phase, AvatarSessionPhase.generating);

      // 재시도 뒤에는 사용자가 "다음" 으로 이어간다. 대기 화면은 없다.
      await tester.tap(_nextButton());
      await _settle(tester);
      expect(advanced, isTrue);
      await session.finish(tester);
    });

    testWidgets('retry is refused without a server call when server says terminal', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _RecoveryClient(serverStatus: 'terminal_failed');
      await tester.pumpWidget(_harness(client));
      await _settle(tester);

      expect(client.retryCalls, 0);
      expect(find.text(avatarTerminalFailureMessage), findsWidgets);
      expect(find.text('다시 시도'), findsNothing);
      expect(find.text(avatarStartOverButtonLabel), findsOneWidget);
    });

    testWidgets('reconciliation_required offers neither retry nor start over', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _RecoveryClient(serverStatus: 'reconciliation_required');
      await tester.pumpWidget(_harness(client));
      await _settle(tester);

      expect(client.retryCalls, 0);
      expect(client.replaceCalls, 0);
      expect(find.text(avatarReconciliationRequiredMessage), findsWidgets);
      expect(find.text('다시 시도'), findsNothing);
      expect(find.text(avatarStartOverButtonLabel), findsNothing);
    });
  });

  group('source_selecting resume', () {
    testWidgets(
      'restart while the server is selecting the source keeps the lock and no error',
      (tester) async {
        await _useMobileSurface(tester);
        final client = _RecoveryClient(serverStatus: 'source_selecting');
        final session = _Session(client);
        final controller = session.controller;
        await tester.pumpWidget(_harness(client, controller: controller));
        await _settle(tester);

        expect(find.byType(AvatarGenerationErrorBanner), findsNothing);
        expect(find.text('아바타 생성중...'), findsNothing);
        expect(find.text(sourceLockedAvatarMessage), findsOneWidget);
        expect(controller.phase, AvatarSessionPhase.generating);
        expect(
          tester.widget<ElevatedButton>(_nextButton()).onPressed,
          isNotNull,
        );
        await session.finish(tester);
      },
    );
  });

  test('resume policy treats source_selecting as active work', () {
    final plan = planAvatarResume(
      AvatarGenerationStatusSnapshot.fromMap({
        'sourceLocked': true,
        'jobId': 'avatar_job_recovery_1',
        'sourceSelectionVersion': 1,
        'status': 'source_selecting',
        'candidateAvailability': 'none',
        'retryAllowed': false,
        'approved': false,
      }),
    );
    expect(plan.action, AvatarResumeAction.resumeGenerating);
    expect(plan.retryAllowed, isFalse);
    expect(plan.allowsNewGeneration, isFalse);
  });
}
