import '../features/onboarding/services/avatar_generation_session_controller.dart';
import '../router/route_names.dart';
import '../shared/utils/avatar_lock_policy.dart';

/// Resolves the first incomplete onboarding step for a stored user profile.
///
/// The resolver is intentionally pure so login, splash recovery, and tests use
/// the same completion rules without reading local storage or Firestore.
String? resolveOnboardingNextRoute(Map<String, dynamic>? profile) {
  final onboarding = profile?['onboarding'];
  if (onboarding is! Map || onboarding.isEmpty) {
    return RouteNames.onboardingBasicInfo;
  }
  if (_isEmpty(onboarding['nickname']) && _isEmpty(onboarding['gender'])) {
    return RouteNames.onboardingBasicInfo;
  }

  final interests = onboarding['interests'];
  if (interests == null || (interests is List && interests.isEmpty)) {
    return RouteNames.onboardingInterestsSelection;
  }

  final lifestyle = onboarding['lifestyle'];
  if (lifestyle == null || (lifestyle is Map && lifestyle.isEmpty)) {
    return RouteNames.onboardingLifestyle;
  }
  if (_isEmpty(onboarding['major'])) {
    return RouteNames.onboardingMajor;
  }

  // 사진 단계는 승인된 아바타가 있거나, 서버가 생성을 받아 잠근 상태(활성 job /
  // source lock)여야 지나간 것으로 본다. 업로드 카운터는 클라이언트가 위조할 수
  // 있으므로 쓰지 않는다. 승인 전 상태는 마지막(아바타 선택) 화면에서 이어간다.
  final approved = _hasApprovedAvatar(profile, onboarding);
  if (!approved && !_hasAvatarGenerationInProgress(profile, onboarding)) {
    return RouteNames.onboardingPhoto;
  }
  if (_isEmpty(onboarding['selfIntroduction'])) {
    return RouteNames.onboardingSelfIntro;
  }

  final profileQa = onboarding['profileQa'];
  if (profileQa == null || (profileQa is List && profileQa.isEmpty)) {
    return RouteNames.onboardingProfileQa;
  }
  final keywords = onboarding['keywords'];
  if (keywords == null || (keywords is List && keywords.isEmpty)) {
    return RouteNames.onboardingKeywords;
  }

  final idealType = profile?['idealType'];
  if (idealType is! Map || idealType.isEmpty) {
    return RouteNames.onboardingIdealType;
  }
  // 건너뛰기는 더 이상 완료를 기록하지 않으므로 skipped 를 완료로 인정한다.
  if (idealType['preferredLifestyles'] == null && idealType['skipped'] != true) {
    return RouteNames.onboardingIdealLifestyle;
  }

  // 나머지가 다 찼는데 아바타만 미승인이면 마지막 단계(선택/대기)로 보낸다.
  if (!approved) {
    return RouteNames.onboardingAvatarSelect;
  }
  return null;
}

bool _isEmpty(dynamic value) {
  if (value == null) return true;
  if (value is String) return value.trim().isEmpty;
  return false;
}

bool _hasApprovedAvatar(Map<String, dynamic>? profile, Map onboarding) {
  final avatarRaw = profile?['avatar'];
  final avatar = avatarRaw is Map ? avatarRaw : const {};
  final status = avatar['status']?.toString().trim().toLowerCase() ?? '';
  if (status == 'approved') return true;

  final avatarUrlsRaw = onboarding['avatarUrls'];
  return avatarUrlsRaw is List &&
      avatarUrlsRaw.whereType<String>().any(isSafePublicApprovedAvatarUrl);
}

/// 서버가 생성을 받아들여 사진이 잠겼거나 작업이 살아 있는 상태.
///
/// `users.avatar.status` 어휘(`userAvatarWorkInProgressStatuses`) 또는 서버가
/// 기록한 `onboarding.avatarGenerationJobId` 로 판정한다. 둘 다 서버만 쓴다.
bool _hasAvatarGenerationInProgress(
  Map<String, dynamic>? profile,
  Map onboarding,
) {
  final avatarRaw = profile?['avatar'];
  final avatar = avatarRaw is Map ? avatarRaw : const {};
  final status = avatar['status']?.toString().trim().toLowerCase() ?? '';
  if (userAvatarWorkInProgressStatuses.contains(status)) return true;
  final jobId = onboarding['avatarGenerationJobId']?.toString().trim() ?? '';
  return jobId.isNotEmpty && status != 'none';
}
