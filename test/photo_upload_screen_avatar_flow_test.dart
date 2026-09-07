import 'package:cloud_functions/cloud_functions.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/screens/photo_upload_screen.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_generation_session_controller.dart';
import 'package:seolleyeon/features/onboarding/services/avatar_resume_policy.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_candidate_selection_dialog.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_error_banner.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_messages.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_models.dart';
import 'package:seolleyeon/services/avatar_generation_client.dart';
import 'package:seolleyeon/services/avatar_source_photo_service.dart';
import 'package:seolleyeon/services/onboarding_photo_source_ref.dart';
import 'package:seolleyeon/shared/utils/avatar_lock_policy.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// admission 만 흉내 내는 클라이언트. 사진 화면은 더 이상 폴링/후보/승인을
/// 하지 않으므로 그 메서드는 호출되면 실패한다.
class _AdmissionClient extends AvatarGenerationClient {
  _AdmissionClient({this.serverStatus, this.serverRetryAllowed = false});

  /// 재진입 복구용 서버 상태. null 이면 상태 조회가 null 을 돌려준다.
  final String? serverStatus;
  final bool serverRetryAllowed;

  int beginCalls = 0;
  int retryCalls = 0;
  int replaceCalls = 0;
  List<OnboardingPhotoSourceRef>? admittedSources;

  @override
  Future<AvatarSourcePhotoUploadResult> beginFromOnboardingPhotos({
    required List<OnboardingPhotoSourceRef> sourcePhotos,
    required String uid,
    String? clientRequestId,
    bool chatPartnerRealPhotoDisclosure = false,
  }) async {
    beginCalls += 1;
    admittedSources = List<OnboardingPhotoSourceRef>.from(sourcePhotos);
    return const AvatarSourcePhotoUploadResult(
      jobId: 'avatar_job_ready_000001',
      photoId: '',
      avatarStatus: 'queued',
      message: 'avatar_generation_queued',
      duplicate: false,
      sourceSelectionVersion: 1,
    );
  }

  @override
  Future<AvatarGenerationStatusSnapshot?> getCurrentGenerationStatus() async {
    if (serverStatus == null) return null;
    return AvatarGenerationStatusSnapshot.fromMap({
      'sourceLocked': true,
      'jobId': 'avatar_job_resume_1',
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
    return AvatarGenerationStatusSnapshot.fromMap({
      'sourceLocked': true,
      'jobId': 'avatar_job_resume_1',
      'sourceSelectionVersion': 1,
      'status': 'queued',
      'candidateAvailability': 'none',
      'retryAllowed': false,
      'approved': false,
    });
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
  Future<AvatarCandidatesResult> pollUntilPreviewReady({
    required String jobId,
    Duration pollInterval = const Duration(seconds: 2),
    Duration timeout = const Duration(seconds: 150),
    bool Function()? shouldContinue,
    int maxConsecutiveErrors =
        AvatarGenerationClient.defaultMaxConsecutivePollErrors,
  }) async => throw StateError('photo screen must not poll');

  @override
  Future<AvatarApprovalResult> approveCandidate(String candidateId) async =>
      throw StateError('photo screen must not approve');
}

class _RejectingAdmissionClient extends _AdmissionClient {
  _RejectingAdmissionClient(this.error);

  final Object error;

  @override
  Future<AvatarSourcePhotoUploadResult> beginFromOnboardingPhotos({
    required List<OnboardingPhotoSourceRef> sourcePhotos,
    required String uid,
    String? clientRequestId,
    bool chatPartnerRealPhotoDisclosure = false,
  }) async {
    beginCalls += 1;
    throw error;
  }
}

Future<void> _useMobileSurface(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(390, 1100);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

const _verifiedRefs = <OnboardingPhotoSourceRef?>[
  OnboardingPhotoSourceRef(
    photoId: 'photo_0001',
    slotIndex: 0,
    objectGeneration: '101',
  ),
  OnboardingPhotoSourceRef(
    photoId: 'photo_0002',
    slotIndex: 1,
    objectGeneration: '102',
  ),
];

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

Widget _harness({
  required AvatarGenerationClient client,
  required void Function(List<String>) onNext,
  AvatarGenerationSessionController? controller,
  List<String?>? initialPhotos,
  List<OnboardingPhotoSourceRef?>? initialSourceRefs,
  String? lockedApprovedAvatarUrl,
}) {
  return MaterialApp(
    home: PhotoUploadScreen(
      avatarGenerationClient: client,
      avatarSessionController: controller,
      initialPhotosForTesting:
          initialPhotos ??
          const [
            'avatar_generation_queued:display_only_1',
            'avatar_generation_queued:display_only_2',
          ],
      initialSourceRefsForTesting: initialSourceRefs ?? _verifiedRefs,
      lockedApprovedAvatarUrlForTesting: lockedApprovedAvatarUrl,
      onNext: onNext,
    ),
  );
}

Finder _nextButton() => find.byType(ElevatedButton).last;

Future<void> _settle(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
}

void _drainExpectedImageLoadException(WidgetTester tester) {
  tester.takeException();
}

void main() {
  group('PhotoUploadScreen avatar flow', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    testWidgets('admission succeeds → advances immediately, no waiting UI', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _AdmissionClient();
      final session = _Session(client);
      List<String>? advancedPhotos;

      await tester.pumpWidget(
        _harness(
          client: client,
          controller: session.controller,
          onNext: (photos) => advancedPhotos = photos,
        ),
      );
      await tester.pump();

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(client.beginCalls, 1);
      expect(advancedPhotos, hasLength(2));
      expect(find.byType(AvatarCandidateSelectionDialog), findsNothing);
      expect(find.text('아바타 생성중...'), findsNothing);
      // 세션 컨트롤러가 job 을 이어받아 생성을 지켜본다.
      expect(session.controller.jobId, isNotEmpty);
      expect(session.controller.phase, AvatarSessionPhase.generating);
      await session.finish(tester);
    });

    testWidgets('two verified uploads are sent together for server selection', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _AdmissionClient();

      await tester.pumpWidget(_harness(client: client, onNext: (_) {}));
      await tester.pump();

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(client.admittedSources?.map((source) => source.photoId), [
        'photo_0001',
        'photo_0002',
      ]);
    });

    testWidgets('사진 없이는 다음 단계로 넘어갈 수 없다', (tester) async {
      await _useMobileSurface(tester);
      List<String>? advancedPhotos;

      await tester.pumpWidget(
        _harness(
          client: _AdmissionClient(),
          initialPhotos: const [],
          initialSourceRefs: const [],
          onNext: (photos) => advancedPhotos = photos,
        ),
      );
      await tester.pump();

      final nextButton = tester.widget<ElevatedButton>(_nextButton());
      expect(nextButton.onPressed, isNull);
      expect(find.text('사진은 나중에 추가할 수 있어요'), findsNothing);
      expect(find.text('최소 2장 필요'), findsOneWidget);

      await tester.tap(_nextButton(), warnIfMissed: false);
      await tester.pump();

      expect(advancedPhotos, isNull);
    });

    testWidgets('an existing queued job advances without a second admission', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      final client = _AdmissionClient();
      final session = _Session(client);
      var advanced = false;

      await tester.pumpWidget(
        _harness(
          client: client,
          controller: session.controller,
          initialPhotos: [
            AvatarSourcePhotoService.queuedSlotToken('job_stale'),
            AvatarSourcePhotoService.queuedSlotToken('job_latest'),
          ],
          initialSourceRefs: const [],
          onNext: (_) => advanced = true,
        ),
      );
      await tester.pump();

      // 합성 슬롯만 있어도(장수 부족) 활성 job 이 있으면 "다음" 은 열려 있다.
      expect(tester.widget<ElevatedButton>(_nextButton()).onPressed, isNotNull);

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(client.beginCalls, 0);
      expect(advanced, isTrue);
      expect(session.controller.jobId, 'job_latest');
      await session.finish(tester);
    });

    testWidgets(
      'back re-entry during generation: photos locked, next re-admits nothing',
      (tester) async {
        await _useMobileSurface(tester);
        final client = _AdmissionClient(serverStatus: 'queued');
        final session = _Session(client);
        var advancedCount = 0;

        await tester.pumpWidget(
          _harness(
            client: client,
            controller: session.controller,
            initialPhotos: [
              AvatarSourcePhotoService.queuedSlotToken('avatar_job_resume_1'),
            ],
            initialSourceRefs: _verifiedRefs,
            onNext: (_) => advancedCount += 1,
          ),
        );
        await _settle(tester);

        // source lock: 삭제 버튼 없음, 잠금 안내.
        expect(find.byIcon(Icons.close_rounded), findsNothing);
        expect(find.text(sourceLockedAvatarMessage), findsOneWidget);

        // 연타해도 admission 은 0회, job 은 그대로다. (하네스에는 실제
        // Navigator 전환이 없어 onNext 횟수 자체는 제한하지 않는다.)
        await tester.tap(_nextButton());
        await tester.tap(_nextButton(), warnIfMissed: false);
        await tester.tap(_nextButton(), warnIfMissed: false);
        await _settle(tester);

        expect(client.beginCalls, 0);
        expect(advancedCount, greaterThanOrEqualTo(1));
        expect(session.controller.jobId, 'avatar_job_resume_1');
        expect(session.controller.phase, AvatarSessionPhase.generating);
        _drainExpectedImageLoadException(tester);
        await session.finish(tester);
      },
    );

    testWidgets(
      'single approved avatar can proceed without another queued source photo',
      (tester) async {
        await _useMobileSurface(tester);
        List<String>? advancedPhotos;

        await tester.pumpWidget(
          _harness(
            client: _AdmissionClient(),
            initialPhotos: const ['https://cdn.example/approved-avatar.png'],
            initialSourceRefs: const [],
            lockedApprovedAvatarUrl: 'https://cdn.example/approved-avatar.png',
            onNext: (photos) => advancedPhotos = photos,
          ),
        );
        await tester.pump();
        _drainExpectedImageLoadException(tester);

        await tester.tap(_nextButton());
        await _settle(tester);
        _drainExpectedImageLoadException(tester);

        expect(advancedPhotos, ['https://cdn.example/approved-avatar.png']);
      },
    );

    testWidgets('approved avatar slot is locked and has no delete button', (
      tester,
    ) async {
      await _useMobileSurface(tester);

      await tester.pumpWidget(
        _harness(
          client: _AdmissionClient(),
          initialPhotos: const ['https://cdn.example/approved-avatar.png'],
          initialSourceRefs: const [],
          lockedApprovedAvatarUrl: 'https://cdn.example/approved-avatar.png',
          onNext: (_) {},
        ),
      );
      await tester.pump();
      _drainExpectedImageLoadException(tester);

      expect(find.text(lockedAvatarNotice), findsOneWidget);
      expect(find.byIcon(Icons.close_rounded), findsNothing);
      expect(find.text('잠김'), findsOneWidget);
    });

    testWidgets('queued avatar source is locked and has no delete button', (
      tester,
    ) async {
      await _useMobileSurface(tester);

      await tester.pumpWidget(
        _harness(
          client: _AdmissionClient(),
          initialPhotos: [
            AvatarSourcePhotoService.queuedSlotToken('job_ready'),
            AvatarSourcePhotoService.queuedSlotToken('job_second'),
          ],
          initialSourceRefs: const [],
          onNext: (_) {},
        ),
      );
      await tester.pump();

      expect(find.text(sourceLockedAvatarMessage), findsOneWidget);
      expect(find.byIcon(Icons.close_rounded), findsNothing);
    });

    testWidgets('admission rejection stays on the photo screen with guidance', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      var advanced = false;

      await tester.pumpWidget(
        _harness(
          client: _RejectingAdmissionClient(
            FirebaseFunctionsException(
              code: 'failed-precondition',
              message: 'avatar_source_set_invalid',
            ),
          ),
          onNext: (_) => advanced = true,
        ),
      );
      await tester.pump();

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(advanced, isFalse);
      expect(find.byType(AvatarCandidateSelectionDialog), findsNothing);
      expect(find.text(avatarSourceSetInvalidMessage), findsWidgets);
      expect(find.byType(AvatarGenerationErrorBanner), findsOneWidget);
    });

    testWidgets('paused generation shows the paused copy', (tester) async {
      await _useMobileSurface(tester);

      await tester.pumpWidget(
        _harness(
          client: _RejectingAdmissionClient(
            FirebaseFunctionsException(
              code: 'failed-precondition',
              message: 'avatar_generation_paused',
            ),
          ),
          onNext: (_) {},
        ),
      );
      await tester.pump();

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(find.text(avatarGenerationPausedMessage), findsWidgets);
    });

    testWidgets('unexpected admission error shows a retryable failure', (
      tester,
    ) async {
      await _useMobileSurface(tester);
      var advanced = false;

      await tester.pumpWidget(
        _harness(
          client: _RejectingAdmissionClient(Exception('network')),
          onNext: (_) => advanced = true,
        ),
      );
      await tester.pump();

      await tester.tap(_nextButton());
      await _settle(tester);

      expect(advanced, isFalse);
      expect(find.text(avatarGenerationFailedMessage), findsWidgets);
      expect(find.text('다시 시도'), findsOneWidget);
      // admission 이 실패했으니 사진은 여전히 바꿀 수 있다.
      expect(find.byIcon(Icons.close_rounded), findsNWidgets(2));
    });

    test('queued tokens do not carry source bytes or refs', () {
      final token = AvatarSourcePhotoService.queuedSlotToken('job_ready');
      expect(token, isNotEmpty);
      expect(token, isNot(contains('gs://')));
      expect(token, isNot(contains('gcs://')));
      expect(token, isNot(contains('sourcePhotoRefs')));
    });

    testWidgets(
      'restart while queued keeps the lock and lets the user move on',
      (tester) async {
        await _useMobileSurface(tester);
        final client = _AdmissionClient(serverStatus: 'queued');
        final session = _Session(client);
        var advanced = false;

        await tester.pumpWidget(
          _harness(
            client: client,
            controller: session.controller,
            initialPhotos: [
              AvatarSourcePhotoService.queuedSlotToken('avatar_job_resume_1'),
            ],
            initialSourceRefs: const [],
            onNext: (_) => advanced = true,
          ),
        );
        await _settle(tester);

        // 서버 작업이 살아 있으므로 실패 배너도, 대기 화면도 없다.
        expect(find.byType(AvatarGenerationErrorBanner), findsNothing);
        expect(find.text('아바타 생성중...'), findsNothing);
        expect(find.text(sourceLockedAvatarMessage), findsOneWidget);
        expect(session.controller.phase, AvatarSessionPhase.generating);

        await tester.tap(_nextButton());
        await _settle(tester);
        expect(advanced, isTrue);
        expect(client.beginCalls, 0);
        _drainExpectedImageLoadException(tester);
        await session.finish(tester);
      },
    );

    testWidgets('restart while needs_review shows review copy and no retry', (
      tester,
    ) async {
      await _useMobileSurface(tester);

      await tester.pumpWidget(
        _harness(
          client: _AdmissionClient(serverStatus: 'needs_review'),
          initialPhotos: [
            AvatarSourcePhotoService.queuedSlotToken('avatar_job_resume_1'),
          ],
          initialSourceRefs: const [],
          onNext: (_) {},
        ),
      );
      await _settle(tester);

      expect(find.text(avatarNeedsReviewMessage), findsOneWidget);
      expect(find.text('다시 시도'), findsNothing);
      expect(find.text(avatarGenerationFailedMessage), findsNothing);
      _drainExpectedImageLoadException(tester);
    });

    testWidgets('restart while terminal_failed offers no retry', (
      tester,
    ) async {
      await _useMobileSurface(tester);

      await tester.pumpWidget(
        _harness(
          client: _AdmissionClient(serverStatus: 'terminal_failed'),
          initialPhotos: [
            AvatarSourcePhotoService.queuedSlotToken('avatar_job_resume_1'),
          ],
          initialSourceRefs: const [],
          onNext: (_) {},
        ),
      );
      await _settle(tester);

      expect(find.text(avatarTerminalFailureMessage), findsOneWidget);
      expect(find.text('다시 시도'), findsNothing);
      _drainExpectedImageLoadException(tester);
    });

    testWidgets(
      'restart while retryable_failed offers retry when server allows',
      (tester) async {
        await _useMobileSurface(tester);

        await tester.pumpWidget(
          _harness(
            client: _AdmissionClient(
              serverStatus: 'retryable_failed',
              serverRetryAllowed: true,
            ),
            initialPhotos: [
              AvatarSourcePhotoService.queuedSlotToken('avatar_job_resume_1'),
            ],
            initialSourceRefs: const [],
            onNext: (_) {},
          ),
        );
        await _settle(tester);

        expect(find.text('다시 시도'), findsOneWidget);
        _drainExpectedImageLoadException(tester);
      },
    );
  });
}
