import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/features/onboarding/screens/photo_upload_screen.dart';
import 'package:seolleyeon/features/onboarding/widgets/avatar_generation_models.dart';
import 'package:seolleyeon/services/avatar_generation_client.dart';

/// 사진 화면 진입 시 워커 pre-warm 한 번. 실패해도 화면은 정상.
class _PrewarmCountingClient extends AvatarGenerationClient {
  _PrewarmCountingClient({this.throwOnPrewarm = false});

  final bool throwOnPrewarm;
  int prewarmCalls = 0;

  @override
  Future<void> prewarmWorker() async {
    prewarmCalls += 1;
    if (throwOnPrewarm) {
      throw StateError('prewarm unavailable');
    }
  }

  @override
  Future<AvatarCandidatesResult> getCandidates(String jobId) async {
    return AvatarCandidatesResult(
      jobId: jobId,
      status: AvatarJobStatus.queued,
      candidates: const [],
    );
  }

  @override
  Future<AvatarApprovalResult> approveCandidate(String candidateId) async {
    throw UnsupportedError('not used');
  }
}

Widget _harness({
  required AvatarGenerationClient client,
  String? lockedApprovedAvatarUrl,
}) {
  return MaterialApp(
    home: PhotoUploadScreen(
      avatarGenerationClient: client,
      initialPhotosForTesting: const <String?>[],
      lockedApprovedAvatarUrlForTesting: lockedApprovedAvatarUrl,
      onNext: (_) {},
    ),
  );
}

void main() {
  testWidgets('entering the photo screen pre-warms the avatar worker once', (
    tester,
  ) async {
    final client = _PrewarmCountingClient();
    await tester.pumpWidget(_harness(client: client));
    await tester.pump();

    expect(client.prewarmCalls, 1);

    // Rebuilds must not re-trigger it.
    await tester.pump(const Duration(milliseconds: 100));
    expect(client.prewarmCalls, 1);
  });

  testWidgets('a locked (already approved) avatar screen does not pre-warm', (
    tester,
  ) async {
    final client = _PrewarmCountingClient();
    await tester.pumpWidget(
      _harness(
        client: client,
        lockedApprovedAvatarUrl:
            'https://storage.googleapis.com/seolleyeon-final-approved-avatars/users/u1/avatar/a.png',
      ),
    );
    await tester.pump();

    expect(client.prewarmCalls, 0);
  });

  testWidgets('a failing pre-warm never surfaces in the photo flow', (
    tester,
  ) async {
    final client = _PrewarmCountingClient(throwOnPrewarm: true);
    await tester.pumpWidget(_harness(client: client));
    await tester.pump();

    expect(client.prewarmCalls, 1);
    expect(tester.takeException(), isNull);
    expect(find.byType(PhotoUploadScreen), findsOneWidget);
  });
}
