# 아바타 선택을 온보딩 마지막 단계로 미루기 (client orchestration)

서버 계약(콜러블·`users.avatar.status`·state-sync·워커)은 바꾸지 않는다. 이 문서는
클라이언트 orchestration 만 설명한다.

## UX 흐름

1. 사진 화면 "다음" = source-set admission(`beginAvatarGenerationFromOnboardingPhotos`) 만
   호출하고 jobId 를 세션 컨트롤러에 넘긴 뒤 **즉시** 자기소개 화면으로 넘어간다.
   대기 화면 없음.
2. 생성은 서버에서 계속된다. 작성 흐름 중간에 `preview_ready + safe 후보` 가 되면
   상단 배너를 3초, job 당 한 번 보여준다.
3. 이상형 단계(저장/건너뛰기 어느 경로든) → `/onboarding/avatar-select`.
   - 생성 중이면 `AvatarGeneratingOverlay` 대기 화면. 준비되면 같은 화면에서 선택 UI 로 전환.
   - 준비됐으면 `AvatarCandidateSelectionDialog` 를 화면 본문으로 재사용.
   - approve → 서버 응답 `approved` 확인 → `completeOnboarding` → 튜토리얼. 승인 실패 시
     완료 기록 없음.
   - 실패 상태는 `planAvatarResume` 결과를 그대로 쓴다. 재시도는 서버가 허용할 때만,
     "사진을 바꾸고 다시 만들기" 는 `replaceAvatarGeneration` 뒤 사진 화면.
     `reconciliation_required` 는 안내만.

## 구성 요소

| 파일 | 역할 |
| --- | --- |
| `lib/features/onboarding/services/avatar_generation_session_controller.dart` | 앱 루트 Provider. `users/{uid}` 스냅샷 리스너 = 변경 트리거, `getCurrentAvatarGenerationStatus` 콜러블 = 확정 상태(safe 후보 여부는 콜러블만 안다). 리스너 실패 시 5초 폴링, 정상이어도 생성 중엔 20초 안전 폴링. 폴링 타이머는 항상 최대 1개. |
| `lib/features/onboarding/widgets/avatar_ready_banner_overlay.dart` | `MaterialApp.builder` 안의 Stack 오버레이. 온보딩 라우트 진입 시 세션 시작, 이탈 시 정지. 배너는 온보딩 라우트이고 마지막 화면이 아니며 앱이 foreground 일 때만 3초. background 에서 완료되면 대기했다가 복귀 후 표시. 마지막 화면 진입 시 즉시 숨김. |
| `lib/services/current_route_observer.dart` | 이름 있는 최상위 라우트를 추적하는 NavigatorObserver. |
| `lib/features/onboarding/screens/avatar_select_screen.dart` | 마지막 단계. 컨트롤러 phase 로 대기/선택/실패 분기. |
| `lib/services/onboarding_route_resolver.dart` | 승인 또는 생성 진행/잠금이면 사진 단계 통과. 나머지가 다 찼는데 미승인이면 `avatar-select`. `idealType.skipped` 를 완료로 인정. |
| `lib/services/onboarding_save_helper.dart` | `completeOnboarding()` 만 완료를 기록한다. 이상형 저장/건너뛰기는 완료를 기록하지 않는다. |

## 격리와 수명

- 배너 once-only 는 **job 단위** (`bannerShownForJobId`). 새 job 은 다시 한 번 뜬다.
- auth uid 가 null 이 되거나 바뀌면 컨트롤러가 `reset()` 으로 job/상태/배너를 전부 비운다.
  auth 감시는 온보딩 밖(`stop()`)에서도 유지된다. 다른 uid 로 다시 시작해도 이전 상태를 비운다.
- 라우트 판정은 `RouteNames.onboardingStepRoutes` 집합. `/onboarding/` prefix 인 보수 라우트
  (`campusLifeZoneRepair`)는 온보딩이 아니다.

## 계약 테스트

- `test/avatar_status_vocabulary_contract_test.dart`: functions 소스의 `users.avatar.status`
  리터럴이 클라이언트 어휘에 1:1 존재.
- `test/onboarding_completion_authority_contract_test.dart`: 아바타 승인 뒤 한 경로만
  `initialSetupComplete` 를 세운다(legacy 사후 완료 경로는 allowlist).
