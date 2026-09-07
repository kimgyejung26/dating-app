/// 온보딩 전체에 걸쳐 살아 있는 아바타 생성 세션.
///
/// 사진 화면은 admission 만 하고 곧바로 다음 단계로 넘어간다. 그 뒤 생성 진행은
/// 이 컨트롤러가 앱 루트에서 지켜보다가, 후보가 준비되면 배너 신호를 내고,
/// 마지막(아바타 선택) 화면이 컨트롤러 상태로 분기한다.
///
/// 상태 소스
/// - 트리거: `users/{uid}` 스냅샷 리스너. `avatar.status` /
///   `onboarding.avatarGenerationJobId` 가 바뀌면 다시 읽는다.
/// - 확정: `getCurrentAvatarGenerationStatus` 콜러블. safe 후보 여부
///   (`candidateAvailability == preview_safe`) 는 사용자 문서에 없고 이 콜러블만
///   계산하므로, 리스너가 본 값으로 직접 행동을 정하지 않는다.
/// - 폴백: 리스너를 열지 못하거나 오류가 나면 짧은 간격 폴링, 리스너가 정상이라도
///   생성 중에는 긴 간격 안전 폴링(state-sync 트리거가 skip 된 경우 대비).
///
/// 격리
/// - 배너 once-only 는 job 단위다(`bannerShownForJobId`). 같은 job 에서는 한 번,
///   replace/재시도로 job 이 바뀌면 다시 한 번 뜰 수 있다.
/// - auth uid 가 null 이 되거나 바뀌면 [reset] 으로 이전 사용자의 job/상태/배너를
///   전부 비운다. auth 감시는 [stop] 뒤에도 살아 있어 온보딩 밖에서 로그아웃해도
///   다음 사용자에게 이전 세션이 새지 않는다.
///
/// 상태 → 행동 매핑은 [planAvatarResume] 을 그대로 재사용한다.
library;

import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import '../../../services/avatar_generation_client.dart';
import '../../../services/storage_service.dart';
import '../../../shared/utils/avatar_lock_policy.dart';
import '../../../shared/utils/privacy_log_utils.dart';
import 'avatar_resume_policy.dart';

/// 서버가 `users/{uid}.avatar.status` 에 기록하는 값의 전체 어휘.
///
/// `functions/src/avatarSourceSetAdmission.ts`(queued, retryable_failed),
/// `avatarGenerationStateSync.ts`(terminal 매핑 + PRESERVED),
/// `avatarApproval.ts`(approval_copying, approved),
/// `avatarGenerationRecovery.ts`(none) 과 1:1 로 맞춘다.
/// `test/avatar_status_vocabulary_contract_test.dart` 가 이 계약을 검사한다.
const Set<String> userAvatarStatusVocabulary = {
  ...sourceLockedAvatarStatuses,
  'approved',
  'approval_copying',
  'approval_copy_failed',
  'completed',
  'cancelled',
  'canceled',
  'none',
};

/// 사용자 문서만 보고 "생성이 시작돼 사진 단계는 지나갔다"고 볼 수 있는 상태.
/// 승인 상태는 포함하지 않는다(승인은 별도 판단).
const Set<String> userAvatarWorkInProgressStatuses = {
  ...sourceLockedAvatarStatuses,
  'approval_copying',
  'approval_copy_failed',
  'completed',
  'cancelled',
  'canceled',
};

enum AvatarSessionPhase {
  /// 진행 중인 작업이 없다(아직 admission 전이거나 replace 로 풀린 상태).
  idle,

  /// 서버 작업이 살아 있다. 마지막 화면은 대기 화면을 보여준다.
  generating,

  /// safe 후보가 준비됐다. 마지막 화면은 선택 UI 를 보여준다.
  previewReady,

  /// needs_review / no_previewable / retryable / terminal / reconciliation.
  /// 마지막 화면에서만 다룬다(작성 흐름 중간에는 배너로 띄우지 않는다).
  attention,

  /// 승인이 끝났다. 마지막 화면은 곧바로 온보딩을 완료한다.
  approved,

  /// 서버 상태를 한 번도 읽지 못했다.
  unavailable,
}

typedef ProfileStreamFactory =
    Stream<Map<String, dynamic>?> Function(String uid);

class AvatarGenerationSessionController extends ChangeNotifier {
  AvatarGenerationSessionController({
    AvatarGenerationClient? client,
    Future<String?> Function()? uidResolver,
    ProfileStreamFactory? profileStreamFactory,
    Stream<String?>? authUidStream,
    this.fallbackPollInterval = const Duration(seconds: 5),
    this.safetyPollInterval = const Duration(seconds: 20),
  }) : _client = client ?? BackendAvatarGenerationClient(),
       _uidResolver = uidResolver,
       _profileStreamFactory = profileStreamFactory,
       _authUidStream = authUidStream;

  final AvatarGenerationClient _client;
  final Future<String?> Function()? _uidResolver;
  final ProfileStreamFactory? _profileStreamFactory;
  final Stream<String?>? _authUidStream;

  /// 리스너가 없거나 실패했을 때의 폴링 간격.
  final Duration fallbackPollInterval;

  /// 리스너가 정상일 때 생성 중에만 도는 안전 폴링 간격.
  final Duration safetyPollInterval;

  AvatarGenerationClient get client => _client;

  String _uid = '';
  String _jobId = '';
  AvatarSessionPhase _phase = AvatarSessionPhase.idle;
  AvatarResumePlan? _plan;
  bool _hasSafeCandidates = false;
  String _bannerShownForJobId = '';
  bool _completionBannerPending = false;
  bool _started = false;
  bool _listenerHealthy = false;
  bool _hasSnapshot = false;
  bool _disposed = false;

  StreamSubscription<Map<String, dynamic>?>? _profileSubscription;
  StreamSubscription<String?>? _authSubscription;
  Timer? _pollTimer;
  Duration? _pollTimerInterval;
  Future<void>? _refreshInFlight;
  bool _refreshRequestedWhileInFlight = false;
  String _lastSeenProfileKey = '';
  Future<void>? _startInFlight;

  String get uid => _uid;
  String get jobId => _jobId;
  AvatarSessionPhase get phase => _phase;
  AvatarResumePlan? get plan => _plan;
  bool get hasSafeCandidates => _hasSafeCandidates;
  bool get isStarted => _started;
  bool get listenerHealthy => _listenerHealthy;

  /// 현재 job 에 대해 완료 배너를 이미 보여줬는가(job 단위 once-only).
  bool get bannerShown => _jobId.isNotEmpty && _bannerShownForJobId == _jobId;

  /// 배너를 보여준 job. 새 job 이 오면 자연히 불일치가 돼 다시 뜰 수 있다.
  String get bannerShownForJobId => _bannerShownForJobId;

  /// "아바타 생성이 완료되었어요" 배너를 아직 보여주지 않았고 보여줘야 한다.
  /// 오버레이가 라우트/앱 상태 조건을 확인한 뒤 [markBannerShown] 으로 소비한다.
  bool get completionBannerPending => _completionBannerPending;

  bool get hasActiveJob => _jobId.isNotEmpty;

  bool get isGenerating => _phase == AvatarSessionPhase.generating;

  /// 폴링 타이머가 살아 있는가. 타이머 누수/중복 검사용.
  @visibleForTesting
  bool get hasPollTimer => _pollTimer != null;

  /// 온보딩 구간에 들어올 때 호출. 여러 번 불러도 한 번만 시작한다.
  Future<void> ensureStarted() {
    if (_disposed) return Future<void>.value();
    if (_started) return _startInFlight ?? Future<void>.value();
    _started = true;
    return _startInFlight = _start();
  }

  Future<void> _start() async {
    try {
      final uid = (await _resolveUid()) ?? '';
      if (_disposed || !_started) return;
      if (_uid.isNotEmpty && uid != _uid) {
        // 다른 계정으로 다시 시작됐다. 이전 사용자의 job/배너를 넘기지 않는다.
        _log('avatar_session_user_changed');
        _clearSessionState();
      }
      _uid = uid;
      _ensureAuthWatch();
      if (uid.isNotEmpty) {
        _subscribeToProfile(uid);
      } else {
        _listenerHealthy = false;
      }
      await refresh();
      _syncPollTimer();
    } finally {
      _startInFlight = null;
    }
  }

  /// admission 이 성공해 jobId 를 받은 직후 사진 화면이 호출한다.
  /// 서버 확인 전이라도 즉시 "생성 중" 으로 전환해 마지막 화면이 대기 UI 를
  /// 보여줄 수 있게 한다.
  Future<void> adoptJob(String jobId) async {
    final normalized = jobId.trim();
    if (_disposed || normalized.isEmpty) return;
    final jobChanged = normalized != _jobId;
    _jobId = normalized;
    _hasSafeCandidates = false;
    _completionBannerPending = false;
    if (jobChanged || _phase != AvatarSessionPhase.generating) {
      _phase = AvatarSessionPhase.generating;
      _plan = AvatarResumePlan(
        action: AvatarResumeAction.resumeGenerating,
        jobId: normalized,
        blocksPhotoEditing: true,
      );
      _notify();
    }
    await ensureStarted();
    if (_disposed) return;
    await refresh();
    _syncPollTimer();
  }

  /// 서버 상태를 다시 읽어 반영한다. 동시 호출은 하나로 합친다.
  Future<void> refresh() {
    if (_disposed) return Future<void>.value();
    final inFlight = _refreshInFlight;
    if (inFlight != null) {
      _refreshRequestedWhileInFlight = true;
      return inFlight;
    }
    return _refreshInFlight = _runRefresh();
  }

  Future<void> _runRefresh() async {
    try {
      AvatarGenerationStatusSnapshot? snapshot;
      try {
        snapshot = await _client.getCurrentGenerationStatus();
      } catch (error) {
        _log('avatar_session_status_failed', error: error);
        snapshot = null;
      }
      if (_disposed) return;
      applySnapshot(snapshot);
    } finally {
      _refreshInFlight = null;
      if (_refreshRequestedWhileInFlight && !_disposed) {
        _refreshRequestedWhileInFlight = false;
        unawaited(refresh());
      }
    }
  }

  /// 순수 상태 전이. 테스트는 이 메서드로 스냅샷 시퀀스를 밀어 넣는다.
  void applySnapshot(AvatarGenerationStatusSnapshot? snapshot) {
    if (_disposed) return;
    final plan = planAvatarResume(snapshot);
    final previousPhase = _phase;

    if (plan.action == AvatarResumeAction.unavailable) {
      // 일시적 조회 실패로 이미 아는 상태를 버리지 않는다.
      if (!_hasSnapshot && _phase == AvatarSessionPhase.idle) {
        _phase = AvatarSessionPhase.unavailable;
        _plan = plan;
        _notify();
      }
      _syncPollTimer();
      return;
    }

    _hasSnapshot = true;
    _plan = plan;
    var jobChanged = false;
    if (plan.jobId.isNotEmpty && plan.jobId != _jobId) {
      // 새 generation(재시도/replace 뒤). 이전 job 의 배너 대기는 무효다.
      jobChanged = true;
      _jobId = plan.jobId;
      _completionBannerPending = false;
    }

    switch (plan.action) {
      case AvatarResumeAction.none:
        _jobId = '';
        _hasSafeCandidates = false;
        _phase = AvatarSessionPhase.idle;
        break;
      case AvatarResumeAction.resumeGenerating:
        _hasSafeCandidates = false;
        _phase = AvatarSessionPhase.generating;
        break;
      case AvatarResumeAction.resumePreview:
        _hasSafeCandidates = true;
        _phase = AvatarSessionPhase.previewReady;
        break;
      case AvatarResumeAction.resumeApproved:
        _hasSafeCandidates = false;
        _phase = AvatarSessionPhase.approved;
        break;
      case AvatarResumeAction.showRetryable:
      case AvatarResumeAction.showNeedsReview:
      case AvatarResumeAction.showReconciliation:
      case AvatarResumeAction.showTerminal:
        _hasSafeCandidates = false;
        _phase = AvatarSessionPhase.attention;
        break;
      case AvatarResumeAction.unavailable:
        break;
    }

    if (_phase == AvatarSessionPhase.previewReady) {
      final enteredPreview =
          previousPhase != AvatarSessionPhase.previewReady || jobChanged;
      if (enteredPreview && !bannerShown) {
        _completionBannerPending = true;
      }
    } else {
      // 준비 상태를 벗어났으면(승인/실패/replace) 밀린 배너는 의미가 없다.
      _completionBannerPending = false;
    }

    _log(
      'avatar_session_phase',
      rawStatus: '${previousPhase.name}->${_phase.name}',
      jobId: _jobId,
    );
    _syncPollTimer();
    _notify();
  }

  /// 오버레이가 배너를 실제로 띄웠거나(또는 마지막 화면이라 띄울 필요가 없어)
  /// 소비했을 때 호출. 같은 job 에서는 다시 띄우지 않는다.
  void markBannerShown() {
    if (!_completionBannerPending && bannerShown) return;
    _completionBannerPending = false;
    _bannerShownForJobId = _jobId;
    _notify();
  }

  /// 리스너/폴링을 멈춘다. 상태는 유지한다(온보딩 구간 이탈).
  ///
  /// auth 감시는 유지한다. 온보딩 밖에서 로그아웃/탈퇴가 일어나도 [reset] 이
  /// 실행돼야 다음 사용자에게 이전 세션이 새지 않는다.
  ///
  /// 구독 취소 Future 는 기다리지 않는다. 취소는 즉시 효력이 있고, 이미 완료된
  /// Future 를 기다리면 fake-async 환경에서 영원히 돌아오지 않는다.
  void stop() {
    _started = false;
    _startInFlight = null;
    _cancelPollTimer();
    _profileSubscription?.cancel();
    _profileSubscription = null;
    _listenerHealthy = false;
    _lastSeenProfileKey = '';
  }

  /// 로그아웃/탈퇴/계정 전환/"사진 바꾸고 다시 만들기" 뒤 세션을 완전히 비운다.
  void reset() {
    stop();
    if (_disposed) return;
    _clearSessionState();
    _notify();
  }

  void _clearSessionState() {
    _uid = '';
    _jobId = '';
    _phase = AvatarSessionPhase.idle;
    _plan = null;
    _hasSafeCandidates = false;
    _bannerShownForJobId = '';
    _completionBannerPending = false;
    _hasSnapshot = false;
    _lastSeenProfileKey = '';
  }

  @override
  void dispose() {
    _disposed = true;
    _cancelPollTimer();
    _profileSubscription?.cancel();
    _profileSubscription = null;
    _authSubscription?.cancel();
    _authSubscription = null;
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // 내부
  // ---------------------------------------------------------------------------

  Future<String?> _resolveUid() async {
    final resolver = _uidResolver;
    if (resolver != null) return resolver();
    try {
      return await StorageService().getKakaoUserId();
    } catch (error) {
      _log('avatar_session_uid_failed', error: error);
      return null;
    }
  }

  /// auth uid 스트림을 한 번만 구독한다. [stop] 에서는 풀지 않는다.
  void _ensureAuthWatch() {
    if (_authSubscription != null) return;
    Stream<String?>? stream = _authUidStream;
    if (stream == null) {
      try {
        stream = FirebaseAuth.instance.authStateChanges().map(
          (user) => user?.uid,
        );
      } catch (error) {
        // Firebase 가 초기화되지 않은 환경(위젯 테스트). auth 감시 없이 진행.
        _log('avatar_session_auth_stream_unavailable', error: error);
        return;
      }
    }
    _authSubscription = stream.listen(
      (uid) {
        if (_disposed) return;
        if (uid == null || uid.isEmpty) {
          // 로그아웃/탈퇴. 리스너를 풀고 상태를 비운다.
          reset();
        } else if (_uid.isNotEmpty && uid != _uid) {
          // 다른 계정. 이전 사용자의 세션을 넘기지 않는다.
          _log('avatar_session_user_changed');
          reset();
        }
      },
      onError: (Object error) {
        _log('avatar_session_auth_stream_error', error: error);
      },
    );
  }

  void _subscribeToProfile(String uid) {
    _profileSubscription?.cancel();
    _profileSubscription = null;
    Stream<Map<String, dynamic>?>? stream;
    try {
      final factory = _profileStreamFactory ?? _defaultProfileStream;
      stream = factory(uid);
    } catch (error) {
      _log('avatar_session_listener_unavailable', error: error);
      _listenerHealthy = false;
      return;
    }
    _listenerHealthy = true;
    _profileSubscription = stream.listen(
      _onProfileEvent,
      onError: (Object error) {
        _log('avatar_session_listener_error', error: error);
        _listenerHealthy = false;
        _syncPollTimer();
      },
    );
  }

  static Stream<Map<String, dynamic>?> _defaultProfileStream(String uid) {
    return FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .snapshots()
        .map((snapshot) => snapshot.data());
  }

  void _onProfileEvent(Map<String, dynamic>? data) {
    if (_disposed) return;
    _listenerHealthy = true;
    final key = profileChangeKey(data);
    final changed = key != _lastSeenProfileKey;
    _lastSeenProfileKey = key;
    if (!changed) return;
    // 사용자 문서는 트리거일 뿐이다. safe 후보 여부는 콜러블로 확정한다.
    unawaited(refresh());
  }

  /// 사용자 문서에서 "다시 읽어야 할 변화" 를 대표하는 키. 로그에 남기지 않는다.
  @visibleForTesting
  static String profileChangeKey(Map<String, dynamic>? data) {
    if (data == null) return '<missing>';
    final avatarRaw = data['avatar'];
    final avatar = avatarRaw is Map ? avatarRaw : const {};
    final onboardingRaw = data['onboarding'];
    final onboarding = onboardingRaw is Map ? onboardingRaw : const {};
    final status = avatar['status']?.toString().trim().toLowerCase() ?? '';
    final jobId = onboarding['avatarGenerationJobId']?.toString().trim() ?? '';
    final approvedUrl = avatar['approvedAvatarUrl']?.toString().trim() ?? '';
    return '$status|$jobId|${approvedUrl.isEmpty ? 0 : 1}';
  }

  void _cancelPollTimer() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _pollTimerInterval = null;
  }

  /// 폴링 타이머는 언제나 최대 하나다. 필요 없으면 지우고, 간격이 바뀌면
  /// 지우고 다시 만든다.
  void _syncPollTimer() {
    if (_disposed || !_started) {
      _cancelPollTimer();
      return;
    }
    final shouldPoll =
        _phase == AvatarSessionPhase.generating ||
        _phase == AvatarSessionPhase.unavailable ||
        (_phase == AvatarSessionPhase.idle && _jobId.isNotEmpty);
    if (!shouldPoll) {
      _cancelPollTimer();
      return;
    }
    final interval = _listenerHealthy
        ? safetyPollInterval
        : fallbackPollInterval;
    if (_pollTimer != null && _pollTimerInterval == interval) return;
    _cancelPollTimer();
    _pollTimerInterval = interval;
    _pollTimer = Timer.periodic(interval, (_) {
      if (_disposed) return;
      unawaited(refresh());
    });
  }

  void _notify() {
    if (_disposed) return;
    notifyListeners();
  }

  void _log(String phase, {String? jobId, String? rawStatus, Object? error}) {
    final parts = <String>['[AvatarFlow]', phase];
    if (jobId != null && jobId.isNotEmpty) {
      parts.add('jobId=${_redactIdentifier(jobId)}');
    }
    if (rawStatus != null) parts.add('rawStatus=$rawStatus');
    if (error != null) {
      parts.add('error=${PrivacyLogUtils.errorSummary(error)}');
    }
    debugPrint(parts.join(' '));
  }

  static String _redactIdentifier(String value) {
    final normalized = value.trim();
    if (normalized.length <= 10) return '<redacted>';
    return '${normalized.substring(0, 10)}...';
  }
}
