import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../router/route_names.dart';
import '../services/avatar_generation_session_controller.dart';

const String avatarReadyBannerTitle = '아바타 생성이 완료되었어요!';
const String avatarReadyBannerBody = '프로필 가입 마지막 화면에서 아바타 사진을 선택할 수 있어요';

/// `MaterialApp.builder` 에 얹는 앱 레벨 오버레이.
///
/// Navigator 위에 있으므로 온보딩 화면 전환에 살아남고, 화면별 Scaffold 나
/// ScaffoldMessenger 에 묶이지 않는다.
///
/// 책임
/// - 라우트가 온보딩 구간([RouteNames.onboardingStepRoutes])에 들어오면 세션
///   컨트롤러를 시작하고, 온보딩 밖으로 나가면 리스너를 멈춘다(앱 재시작 후
///   작성 흐름 중간에 들어와도 배너가 뜬다).
/// - 컨트롤러가 처음으로 `preview_ready + safe 후보` 로 전이해
///   [AvatarGenerationSessionController.completionBannerPending] 이 서면, 현재
///   라우트가 온보딩 구간이고 마지막(아바타 선택) 화면이 아니며 앱이 foreground
///   일 때만 상단 슬라이드 배너를 [displayDuration] 동안 보여준 뒤
///   `markBannerShown` 으로 소비한다. 앱이 background 이면 대기 상태를 유지했다가
///   foreground 로 돌아온 뒤 보여준다.
/// - 마지막 화면에 있으면 배너 없이 소비한다(그 화면이 곧바로 선택 UI 로 바뀐다).
///   배너 표시 중 마지막 화면으로 들어가면 즉시 숨긴다.
/// - 실패 상태는 여기서 띄우지 않는다. 마지막 화면에서만 다룬다.
class AvatarReadyBannerOverlay extends StatefulWidget {
  const AvatarReadyBannerOverlay({
    super.key,
    required this.controller,
    required this.currentRouteName,
    required this.child,
    this.displayDuration = const Duration(seconds: 3),
  });

  final AvatarGenerationSessionController controller;
  final ValueListenable<String?> currentRouteName;
  final Widget child;
  final Duration displayDuration;

  @override
  State<AvatarReadyBannerOverlay> createState() =>
      _AvatarReadyBannerOverlayState();
}

class _AvatarReadyBannerOverlayState extends State<AvatarReadyBannerOverlay>
    with WidgetsBindingObserver {
  bool _visible = false;
  Timer? _hideTimer;
  bool _wasInOnboarding = false;
  AppLifecycleState? _lifecycleState;

  /// 앱이 화면에 보이는 상태인가. 알 수 없으면(초기) foreground 로 본다.
  bool get _isForeground {
    final state = _lifecycleState ?? WidgetsBinding.instance.lifecycleState;
    return state == null || state == AppLifecycleState.resumed;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _lifecycleState = WidgetsBinding.instance.lifecycleState;
    widget.controller.addListener(_evaluate);
    widget.currentRouteName.addListener(_onRouteChanged);
    _onRouteChanged();
  }

  @override
  void didUpdateWidget(covariant AvatarReadyBannerOverlay oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_evaluate);
      widget.controller.addListener(_evaluate);
    }
    if (oldWidget.currentRouteName != widget.currentRouteName) {
      oldWidget.currentRouteName.removeListener(_onRouteChanged);
      widget.currentRouteName.addListener(_onRouteChanged);
    }
  }

  @override
  void dispose() {
    _hideTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    widget.controller.removeListener(_evaluate);
    widget.currentRouteName.removeListener(_onRouteChanged);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _lifecycleState = state;
    if (state == AppLifecycleState.resumed) {
      // background 에서 생성이 끝났다면 지금 보여준다.
      _evaluate();
    }
  }

  void _onRouteChanged() {
    final route = widget.currentRouteName.value;
    final inOnboarding = RouteNames.isOnboardingRoute(route);
    if (inOnboarding && !_wasInOnboarding) {
      unawaited(widget.controller.ensureStarted());
    } else if (!inOnboarding && _wasInOnboarding && route != null) {
      // 튜토리얼/메인으로 넘어갔다. 리스너를 유지할 이유가 없다.
      widget.controller.stop();
    }
    _wasInOnboarding = inOnboarding;
    if (_visible && route == RouteNames.onboardingAvatarSelect) {
      // 마지막 화면은 선택 UI 자체가 안내다. 배너를 겹치지 않는다.
      _hide();
    }
    _evaluate();
  }

  void _evaluate() {
    if (!mounted) return;
    final controller = widget.controller;
    if (!controller.completionBannerPending) return;
    final route = widget.currentRouteName.value;
    if (!RouteNames.isOnboardingRoute(route)) return;
    if (route == RouteNames.onboardingAvatarSelect) {
      // 마지막 화면은 컨트롤러 상태로 곧바로 선택 UI 를 보여준다.
      controller.markBannerShown();
      return;
    }
    if (!_isForeground) {
      // background 에서 3초를 소비하지 않는다. foreground 복귀 때 보여준다.
      return;
    }
    controller.markBannerShown();
    _show();
  }

  void _show() {
    _hideTimer?.cancel();
    setState(() => _visible = true);
    _hideTimer = Timer(widget.displayDuration, () {
      if (!mounted) return;
      setState(() => _visible = false);
    });
  }

  void _hide() {
    _hideTimer?.cancel();
    _hideTimer = null;
    if (!_visible) return;
    setState(() => _visible = false);
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      textDirection: TextDirection.ltr,
      children: [
        widget.child,
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: IgnorePointer(
            ignoring: !_visible,
            child: AnimatedSlide(
              duration: const Duration(milliseconds: 260),
              curve: Curves.easeOutCubic,
              offset: _visible ? Offset.zero : const Offset(0, -1.2),
              child: AnimatedOpacity(
                duration: const Duration(milliseconds: 200),
                opacity: _visible ? 1 : 0,
                child: const _AvatarReadyBanner(),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _AvatarReadyBanner extends StatelessWidget {
  const _AvatarReadyBanner();

  static const Color _deepPlum = Color(0xFF32172A);
  static const Color _warmOffWhite = Color(0xFFF9F9F7);
  static const Color _textSecondary = Color(0xFF6B5A66);

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
        child: Material(
          key: const ValueKey('avatar_ready_banner'),
          color: _warmOffWhite,
          elevation: 8,
          shadowColor: _deepPlum.withValues(alpha: 0.25),
          borderRadius: BorderRadius.circular(18),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.check_circle_rounded,
                  color: _deepPlum,
                  size: 22,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        avatarReadyBannerTitle,
                        style: TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: _deepPlum,
                          decoration: TextDecoration.none,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        avatarReadyBannerBody,
                        style: TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 13,
                          color: _textSecondary,
                          height: 1.4,
                          decoration: TextDecoration.none,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
