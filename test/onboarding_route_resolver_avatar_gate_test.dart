import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/router/route_names.dart';
import 'package:seolleyeon/services/onboarding_route_resolver.dart';

/// 온보딩 재개(resume) 라우팅의 사진/아바타 게이트 회귀 테스트.
///
/// 사진 단계는 "승인된 아바타" 또는 "서버가 생성을 받아들여 잠근 상태"여야
/// 지나간다. 과거처럼 sourcePhotoUploadCount 카운터(클라이언트 위조 가능)만으로는
/// 통과할 수 없다. 나머지 단계가 다 찼는데 미승인이면 마지막(아바타 선택)
/// 화면으로 보낸다.
Map<String, dynamic> _baseProfile({
  Map<String, dynamic>? avatar,
  Map<String, dynamic>? onboardingOverrides,
  Map<String, dynamic>? idealType,
}) {
  return <String, dynamic>{
    if (avatar != null) 'avatar': avatar,
    'onboarding': <String, dynamic>{
      'nickname': 'tester',
      'gender': 'female',
      'interests': ['movie'],
      'lifestyle': <String, dynamic>{'drinking': 'none'},
      'major': 'humanities',
      'sourcePhotoUploadCount': 2,
      'selfIntroduction': 'hello',
      'profileQa': [
        {'question': 'q', 'answer': 'a'},
      ],
      'keywords': ['calm'],
      ...?onboardingOverrides,
    },
    'idealType':
        idealType ??
        <String, dynamic>{
          'preferredLifestyles': ['calm'],
        },
  };
}

void main() {
  group('resolveOnboardingNextRoute avatar gate', () {
    test('업로드 카운터만으로는 사진 단계를 통과할 수 없다', () {
      final profile = _baseProfile();

      expect(resolveOnboardingNextRoute(profile), RouteNames.onboardingPhoto);
    });

    test('승인된 아바타 상태가 있으면 온보딩이 끝난 것으로 본다', () {
      final profile = _baseProfile(
        avatar: <String, dynamic>{'status': 'approved'},
      );

      expect(resolveOnboardingNextRoute(profile), isNull);
    });

    test('onboarding.avatarUrls에 안전한 승인 URL이 있으면 통과한다', () {
      final profile = _baseProfile();
      (profile['onboarding'] as Map<String, dynamic>)['avatarUrls'] = [
        'https://firebasestorage.googleapis.com/v0/b/approved/o/avatar.png',
      ];

      expect(resolveOnboardingNextRoute(profile), isNull);
    });

    test('안전하지 않은 URL만 있으면 사진 단계로 되돌린다', () {
      final profile = _baseProfile();
      (profile['onboarding'] as Map<String, dynamic>)['avatarUrls'] = [
        'gs://seolleyeon-final-avatar-temp/users/u1/jobs/j/candidates/c.png',
      ];

      expect(resolveOnboardingNextRoute(profile), RouteNames.onboardingPhoto);
    });

    test('생성 진행 중(미승인)이고 나머지가 다 찼으면 아바타 선택 화면으로 보낸다', () {
      for (final status in const [
        'queued',
        'source_selecting',
        'preview_ready',
        'needs_review',
        'retryable_failed',
        'terminal_failed',
        'reconciliation_required',
        'approval_copying',
      ]) {
        final profile = _baseProfile(
          avatar: <String, dynamic>{'status': status},
        );

        expect(
          resolveOnboardingNextRoute(profile),
          RouteNames.onboardingAvatarSelect,
          reason: '$status must reach the avatar select step',
        );
      }
    });

    test('생성 진행 중이면 사진 단계는 지나가고 빈 단계로 이어진다', () {
      final profile = _baseProfile(
        avatar: <String, dynamic>{'status': 'queued'},
        onboardingOverrides: <String, dynamic>{'selfIntroduction': ''},
      );

      expect(
        resolveOnboardingNextRoute(profile),
        RouteNames.onboardingSelfIntro,
      );
    });

    test('서버가 기록한 jobId 만 있어도 사진 단계는 지나간다', () {
      final profile = _baseProfile(
        onboardingOverrides: <String, dynamic>{
          'avatarGenerationJobId': 'avatar_job_abcdefgh12',
        },
      );

      expect(
        resolveOnboardingNextRoute(profile),
        RouteNames.onboardingAvatarSelect,
      );
    });

    test('replace 로 풀린 상태(none)는 사진 단계로 되돌린다', () {
      final profile = _baseProfile(
        avatar: <String, dynamic>{'status': 'none'},
        onboardingOverrides: <String, dynamic>{
          'avatarGenerationJobId': 'avatar_job_abcdefgh12',
        },
      );

      expect(resolveOnboardingNextRoute(profile), RouteNames.onboardingPhoto);
    });

    test('이상형 건너뛰기(skipped)는 lifestyle 완료로 인정한다', () {
      final profile = _baseProfile(
        avatar: <String, dynamic>{'status': 'queued'},
        idealType: <String, dynamic>{'skipped': true},
      );

      expect(
        resolveOnboardingNextRoute(profile),
        RouteNames.onboardingAvatarSelect,
      );
    });

    test('이상형이 비어 있으면 아바타 선택보다 이상형 단계가 먼저다', () {
      final profile = _baseProfile(
        avatar: <String, dynamic>{'status': 'queued'},
        idealType: <String, dynamic>{},
      );

      expect(
        resolveOnboardingNextRoute(profile),
        RouteNames.onboardingIdealType,
      );
    });
  });
}
