// =============================================================================
// 오늘의 인연 (미스터리 카드) 화면
// 경로: lib/features/matching/screens/mystery_card_screen.dart
//
// PageView 기반 스와이프 캐러셀 + 카드별 3D 플립 애니메이션
// 1차 탭: 미스터리 → 프로필 공개 (플립)
// 2차 탭: ai_match_card_screen으로 이동
// =============================================================================

import 'dart:math';
import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF4D88);
  static const Color purple100 = Color(0xFFEDE9FE);
  static const Color purple600 = Color(0xFF9333EA);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray300 = Color(0xFFD1D5DB);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color gray500 = Color(0xFF6B7280);
  static const Color gray900 = Color(0xFF111827);
  static const Color pink50 = Color(0xFFFDF2F8);
  static const Color pink100 = Color(0xFFFCE7F3);
  static const Color pink500 = Color(0xFFEC4899);
}

// =============================================================================
// 프로필 데이터 모델 (목업)
// =============================================================================
class _MockProfile {
  final String id;
  final String name;
  final int matchPercent;
  final String major;
  final String year;
  final List<String> tags;
  final String imageUrl;

  const _MockProfile({
    required this.id,
    required this.name,
    required this.matchPercent,
    required this.major,
    required this.year,
    required this.tags,
    required this.imageUrl,
  });
}

// 목업 프로필 5개
const List<_MockProfile> _mockProfiles = [
  _MockProfile(
    id: 'p1',
    name: 'Ji-min',
    matchPercent: 94,
    major: 'Business Admin',
    year: "'01",
    tags: ['TRAVEL', 'COFFEE', 'MUSIC'],
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuA-iKoOfd7mUBhLCu8omhZBXx588zQSVaTuUyPxd8tn5HGIqbofexG6xV_wpU-m1DwzanC-9eZa9On_1heZiGjjrRZfW2q-4u5XMCegZ3-FWSb_vFcW2Q-ekVQFZTaKtT8ja--_6YV71R2iJjLA0J91Y1Jnp0SbXNEjmIBvH9TIoHyXY-ErSnUZaRjEhcBVmhOpChRqBrF0r5YpiKtqSi8G8DdMop8R7kiJGLKFoChyCmRyqHE7EB-Km7q6kjBctextaAUtbZwKHDEX',
  ),
  _MockProfile(
    id: 'p2',
    name: 'Soo-yeon',
    matchPercent: 91,
    major: 'Visual Design',
    year: "'02",
    tags: ['ART', 'YOGA', 'READING'],
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuDpIxhHnYDkmD9z4U531npC8ZOpcgsNx5XJm96MbnNDjgdLpbH0-ZITCknT1WQTMor_kO8HJdn9gYk-VqSrCCin6Lx5nw-vM6QKH_lv1Mh8MPEypmEUXk3zczihAiAPhOMJYJgtEyA6ObIcE6qlGhH-23M6k6HTvLH57RtTbCprjgrx7Wg7Dy55ajq_YM9ABafQfkWyfZeAAX0qoE69mVQk2hACXRj6HRcmBira18n_hGrYPZEdP209XcwjPxAWn_op8Va1qvtAaD6P',
  ),
  _MockProfile(
    id: 'p3',
    name: 'Ha-eun',
    matchPercent: 88,
    major: 'Computer Science',
    year: "'00",
    tags: ['GAMING', 'COOKING', 'K-POP'],
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuAH9LSr17vPuJIj8r0HFM32qC-F4R82GKlZPXkHBeBzABCbmz34c6lD28TrhlsHLm1FjEx_bbK50RrE0y_qMRJkmAuZpJDwgarEozkvS9AMZ7YNakmwZd2utYjJQRK34IDrApfQIcjNA2owpPx2hAP0Qs4QBx16UgAaCd6WoQQPEzyM8J7dQFvy-bVjKEvlFmPUXYeYwtNEeSjuZN6XFDwesfWAvBndhVt9wWu3hLo2J3LrVEbzUr5N-Scj5PZPfLbscATh-7qgtWzB',
  ),
  _MockProfile(
    id: 'p4',
    name: 'Ye-jin',
    matchPercent: 85,
    major: 'Psychology',
    year: "'01",
    tags: ['FILM', 'CAFE', 'HIKING'],
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuBdDzeTNFzJ93Ao1Ro1vOQA6dFa-jLmjdHvDmahzvVkE3zoMZkpdM9qvXEKKrar6Zz-OxEeTQ3-tsnLbNsNpawJKdQuUDC7w794c2LbS7jyga-5qbK_Cg-JOBw56EBUe9YAv3v5hME6IG-2yVgc1Y5kZG44wzXy9gdb6I40-yNOBrvZtDDFcJWOtQi4TMCc24XYEKi-sGP4grGxPQ8ifSO9BKc7b0TK_UH39lb7hIq0N1Rp9SDeCqGYla6MHfghw1A56h6ivxEke0HR',
  ),
  _MockProfile(
    id: 'p5',
    name: 'Min-seo',
    matchPercent: 82,
    major: 'Architecture',
    year: "'03",
    tags: ['PHOTO', 'DANCE', 'WINE'],
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuA-iKoOfd7mUBhLCu8omhZBXx588zQSVaTuUyPxd8tn5HGIqbofexG6xV_wpU-m1DwzanC-9eZa9On_1heZiGjjrRZfW2q-4u5XMCegZ3-FWSb_vFcW2Q-ekVQFZTaKtT8ja--_6YV71R2iJjLA0J91Y1Jnp0SbXNEjmIBvH9TIoHyXY-ErSnUZaRjEhcBVmhOpChRqBrF0r5YpiKtqSi8G8DdMop8R7kiJGLKFoChyCmRyqHE7EB-Km7q6kjBctextaAUtbZwKHDEX',
  ),
];

// =============================================================================
// 메인 화면
// =============================================================================
class MysteryCardScreen extends StatelessWidget {
  final int notificationCount;
  final int remainingMatches;
  final VoidCallback? onAiPreference;
  final VoidCallback? onNotification;
  final VoidCallback? onSettings;
  final Function(int index)? onNavTap;

  const MysteryCardScreen({
    super.key,
    this.notificationCount = 1,
    this.remainingMatches = 2,
    this.onAiPreference,
    this.onNotification,
    this.onSettings,
    this.onNavTap,
  });

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: CupertinoColors.white,
      child: Stack(
        children: [
          // 배경 그라데이션
          _BackgroundGradients(),
          // 메인 콘텐츠
          SafeArea(
            child: Column(
              children: [
                // 헤더
                _Header(
                  notificationCount: notificationCount,
                  onAiPreference:
                      onAiPreference ??
                      () => Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushNamed(RouteNames.profileCard),
                  onNotification: onNotification,
                ),
                // 메인 콘텐츠 (StatefulWidget으로 인디케이터 관리)
                Expanded(
                  child: _MainContent(
                    remainingMatches: remainingMatches,
                    onSettings: onSettings,
                  ),
                ),
              ],
            ),
          ),
          // 하단 네비게이션
          Positioned(
            left: 20,
            right: 20,
            bottom: bottomPadding + 24,
            child: _FloatingNavBar(onTap: onNavTap),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 배경 그라데이션
// =============================================================================
class _BackgroundGradients extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          top: -100,
          left: -100,
          child: Container(
            width: 400,
            height: 400,
            decoration: BoxDecoration(
              color: const Color(0xFFFBCFE8).withValues(alpha: 0.3),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 100, sigmaY: 100),
              child: const SizedBox(),
            ),
          ),
        ),
        Positioned(
          bottom: -100,
          right: -100,
          child: Container(
            width: 500,
            height: 500,
            decoration: BoxDecoration(
              color: const Color(0xFFE9D5FF).withValues(alpha: 0.3),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 100, sigmaY: 100),
              child: const SizedBox(),
            ),
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final int notificationCount;
  final VoidCallback? onAiPreference;
  final VoidCallback? onNotification;

  const _Header({
    required this.notificationCount,
    this.onAiPreference,
    this.onNotification,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 로고
          Row(
            children: [
              const Icon(
                CupertinoIcons.heart_fill,
                size: 24,
                color: _AppColors.primary,
              ),
              const SizedBox(width: 8),
              const Text(
                '설레연',
                style: TextStyle(
                  fontFamily: '.SF Pro Display',
                  fontSize: 21,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.3,
                  color: _AppColors.gray900,
                ),
              ),
            ],
          ),
          // 버튼들
          Row(
            children: [
              // AI 취향 버튼
              CupertinoButton(
                padding: EdgeInsets.zero,
                onPressed: onAiPreference,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: _AppColors.pink50,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: _AppColors.pink100),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        CupertinoIcons.sparkles,
                        size: 16,
                        color: _AppColors.pink500,
                      ),
                      const SizedBox(width: 6),
                      const Text(
                        'AI에게 내 취향 알려주기',
                        style: TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: _AppColors.gray900,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              // 알림 버튼
              CupertinoButton(
                padding: EdgeInsets.zero,
                onPressed: onNotification,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    const Icon(
                      CupertinoIcons.bell,
                      size: 24,
                      color: _AppColors.gray500,
                    ),
                    if (notificationCount > 0)
                      Positioned(
                        top: -4,
                        right: -4,
                        child: Container(
                          width: 16,
                          height: 16,
                          decoration: BoxDecoration(
                            color: _AppColors.primary,
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: CupertinoColors.white,
                              width: 2,
                            ),
                          ),
                          child: Center(
                            child: Text(
                              '$notificationCount',
                              style: const TextStyle(
                                fontFamily: '.SF Pro Text',
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: CupertinoColors.white,
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 메인 콘텐츠 (StatefulWidget — 인디케이터 인덱스 관리)
// =============================================================================
class _MainContent extends StatefulWidget {
  final int remainingMatches;
  final VoidCallback? onSettings;

  const _MainContent({required this.remainingMatches, this.onSettings});

  @override
  State<_MainContent> createState() => _MainContentState();
}

class _MainContentState extends State<_MainContent> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 0),
      child: Column(
        children: [
          const SizedBox(height: 16),
          // 타이틀 영역
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: _AppColors.purple100,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'AI CURATED',
                            style: TextStyle(
                              fontFamily: '.SF Pro Text',
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              color: _AppColors.purple600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'Nov 14',
                          style: TextStyle(
                            fontFamily: '.SF Pro Text',
                            fontSize: 12,
                            color: _AppColors.gray400,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '오늘의 인연',
                      style: TextStyle(
                        fontFamily: '.SF Pro Display',
                        fontSize: 30,
                        fontWeight: FontWeight.w500,
                        letterSpacing: -0.5,
                        color: _AppColors.gray900,
                      ),
                    ),
                  ],
                ),
                CupertinoButton(
                  padding: EdgeInsets.zero,
                  onPressed: () {
                    Navigator.of(
                      context,
                      rootNavigator: true,
                    ).pushNamed(RouteNames.sentHearts);
                  },
                  child: const Icon(
                    CupertinoIcons.heart,
                    size: 24,
                    color: _AppColors.gray400,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          // ─── PageView 기반 카드 캐러셀 ───
          Expanded(
            child: _CardCarousel(
              profiles: _mockProfiles,
              onPageChanged: (index) {
                setState(() => _currentIndex = index);
              },
            ),
          ),
          const SizedBox(height: 24),
          // ─── 동적 인디케이터 (profiles.length 기반) ───
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(_mockProfiles.length, (i) {
              return Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: i == _currentIndex
                      ? _AppColors.gray900
                      : _AppColors.gray300,
                  shape: BoxShape.circle,
                ),
              );
            }),
          ),
          const SizedBox(height: 24),
          // 남은 매치 안내
          Text(
            'You have ${widget.remainingMatches} curated matches remaining today',
            style: const TextStyle(
              fontFamily: '.SF Pro Text',
              fontSize: 12,
              fontWeight: FontWeight.w300,
              color: _AppColors.gray400,
            ),
          ),
          const SizedBox(height: 100),
        ],
      ),
    );
  }
}

// =============================================================================
// 카드 캐러셀 (PageView.builder 기반)
//
// - PageController(viewportFraction: 0.82) → 다음 카드 일부 보임
// - onPageChanged → 부모에 currentIndex 전달
// - 활성 페이지: scale 1.0, opacity 1.0
// - 비활성 페이지: scale 0.95, opacity 0.55
// =============================================================================
class _CardCarousel extends StatefulWidget {
  final List<_MockProfile> profiles;
  final ValueChanged<int>? onPageChanged;

  const _CardCarousel({required this.profiles, this.onPageChanged});

  @override
  State<_CardCarousel> createState() => _CardCarouselState();
}

class _CardCarouselState extends State<_CardCarousel> {
  late final PageController _pageController;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(viewportFraction: 0.82);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PageView.builder(
      controller: _pageController,
      itemCount: widget.profiles.length,
      physics: const BouncingScrollPhysics(),
      onPageChanged: (index) {
        setState(() => _currentIndex = index);
        widget.onPageChanged?.call(index);
      },
      itemBuilder: (context, index) {
        final isActive = index == _currentIndex;
        return AnimatedScale(
          scale: isActive ? 1.0 : 0.95,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
          child: AnimatedOpacity(
            opacity: isActive ? 1.0 : 0.55,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            child: Center(
              child: _MysteryCard(
                key: ValueKey(widget.profiles[index].id),
                profile: widget.profiles[index],
                isActive: isActive,
              ),
            ),
          ),
        );
      },
    );
  }
}

// =============================================================================
// 미스터리 카드 (3D 플립 애니메이션)
//
// - AutomaticKeepAliveClientMixin으로 플립 상태 유지
// - 1차 탭: 미스터리 → 프로필 플립
// - 2차 탭: ai_match_card_screen 이동
// =============================================================================
class _MysteryCard extends StatefulWidget {
  final _MockProfile profile;
  final bool isActive;

  const _MysteryCard({
    super.key,
    required this.profile,
    required this.isActive,
  });

  @override
  State<_MysteryCard> createState() => _MysteryCardState();
}

class _MysteryCardState extends State<_MysteryCard>
    with SingleTickerProviderStateMixin, AutomaticKeepAliveClientMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  bool _isRevealed = false;

  // AutomaticKeepAliveClientMixin: 스와이프해도 플립 상태 유지
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 700),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOutCubic),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onCardTap() {
    if (!widget.isActive || _controller.isAnimating) return;

    if (_isRevealed) {
      // 2차 탭: ai_match_card_screen으로 이동
      HapticFeedback.lightImpact();
      Future.delayed(const Duration(milliseconds: 150), () {
        if (!mounted) return;
        Navigator.of(
          context,
          rootNavigator: true,
        ).pushNamed(RouteNames.profileSpecificDetail);
      });
    } else {
      // 1차 탭: 플립 애니메이션으로 프로필 공개
      HapticFeedback.mediumImpact();
      _controller.forward().then((_) {
        if (mounted) setState(() => _isRevealed = true);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context); // AutomaticKeepAliveClientMixin 필수 호출
    final screenWidth = MediaQuery.of(context).size.width;
    final cardWidth = screenWidth * 0.75;
    final cardHeight = cardWidth * 1.33;

    return GestureDetector(
      onTap: _onCardTap,
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          final angle = _animation.value * pi;
          final isBackVisible = _animation.value >= 0.5;

          return Transform(
            alignment: Alignment.center,
            transform: Matrix4.identity()
              ..setEntry(3, 2, 0.001) // perspective
              ..rotateY(angle),
            child: isBackVisible
                ? _buildBackFace(cardWidth, cardHeight)
                : _buildFrontFace(cardWidth, cardHeight),
          );
        },
      ),
    );
  }

  /// 앞면: 미스터리 '?' 카드
  Widget _buildFrontFace(double cardWidth, double cardHeight) {
    return Container(
      width: cardWidth,
      height: cardHeight,
      decoration: BoxDecoration(
        color: CupertinoColors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _AppColors.gray100),
        boxShadow: widget.isActive
            ? [
                BoxShadow(
                  color: CupertinoColors.black.withValues(alpha: 0.15),
                  blurRadius: 60,
                  offset: const Offset(0, 30),
                ),
                BoxShadow(
                  color: CupertinoColors.black.withValues(alpha: 0.04),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ]
            : null,
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 배경 원
          Container(
            width: 160,
            height: 160,
            decoration: BoxDecoration(
              color: _AppColors.primary.withValues(
                alpha: widget.isActive ? 0.1 : 0.05,
              ),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
              child: const SizedBox(),
            ),
          ),
          // 물음표
          Text(
            '?',
            style: TextStyle(
              fontFamily: '.SF Pro Display',
              fontSize: 128,
              fontWeight: FontWeight.w700,
              color: widget.isActive
                  ? _AppColors.primary
                  : _AppColors.primary.withValues(alpha: 0.7),
            ),
          ),
          // 탭 힌트 (활성 카드만)
          if (widget.isActive)
            Positioned(
              bottom: 24,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: _AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      CupertinoIcons.hand_draw,
                      size: 16,
                      color: _AppColors.primary,
                    ),
                    SizedBox(width: 6),
                    Text(
                      '탭하여 확인하기',
                      style: TextStyle(
                        fontFamily: '.SF Pro Text',
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: _AppColors.primary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// 뒷면: 프로필 카드 프리뷰 (좌우 반전 보정, 프로필 데이터 사용)
  Widget _buildBackFace(double cardWidth, double cardHeight) {
    final profile = widget.profile;
    return Transform(
      alignment: Alignment.center,
      transform: Matrix4.identity()..rotateY(pi), // 거울 보정
      child: Container(
        width: cardWidth,
        height: cardHeight,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: _AppColors.primary.withValues(alpha: 0.25),
              blurRadius: 40,
              offset: const Offset(0, 20),
            ),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // 프로필 이미지
            Image.network(
              profile.imageUrl,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                  Container(color: _AppColors.gray300),
            ),
            // 그라데이션 오버레이
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    CupertinoColors.black.withValues(alpha: 0),
                    CupertinoColors.black.withValues(alpha: 0.15),
                    CupertinoColors.black.withValues(alpha: 0.75),
                  ],
                  stops: const [0.0, 0.5, 1.0],
                ),
              ),
            ),
            // 프로필 정보
            Positioned(
              left: 24,
              right: 24,
              bottom: 24,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 이름 + 매치율
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          profile.name,
                          style: const TextStyle(
                            fontFamily: '.SF Pro Display',
                            fontSize: 28,
                            fontWeight: FontWeight.w600,
                            color: CupertinoColors.white,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: CupertinoColors.white.withValues(
                                alpha: 0.2,
                              ),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: CupertinoColors.white.withValues(
                                  alpha: 0.1,
                                ),
                              ),
                            ),
                            child: Text(
                              '${profile.matchPercent}% Match',
                              style: const TextStyle(
                                fontFamily: '.SF Pro Text',
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: CupertinoColors.white,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  // 학과 + 학번
                  Text(
                    "${profile.major} • ${profile.year}",
                    style: TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 14,
                      fontWeight: FontWeight.w300,
                      color: CupertinoColors.white.withValues(alpha: 0.8),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 12),
                  // 태그 칩
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: profile.tags.map((tag) {
                      return ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 4, sigmaY: 4),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 5,
                            ),
                            decoration: BoxDecoration(
                              color: CupertinoColors.black.withValues(
                                alpha: 0.35,
                              ),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: CupertinoColors.white.withValues(
                                  alpha: 0.1,
                                ),
                              ),
                            ),
                            child: Text(
                              tag,
                              style: const TextStyle(
                                fontFamily: '.SF Pro Text',
                                fontSize: 11,
                                fontWeight: FontWeight.w500,
                                color: CupertinoColors.white,
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 플로팅 네비게이션
// =============================================================================
class _FloatingNavBar extends StatelessWidget {
  final Function(int index)? onTap;

  const _FloatingNavBar({this.onTap});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(32),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 24),
          decoration: BoxDecoration(
            color: CupertinoColors.white.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: _AppColors.gray100),
            boxShadow: [
              BoxShadow(
                color: CupertinoColors.black.withValues(alpha: 0.05),
                blurRadius: 20,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _NavItem(
                icon: CupertinoIcons.heart_fill,
                label: '설레연',
                isActive: true,
                onTap: () => onTap?.call(0),
              ),
              _NavItem(
                icon: CupertinoIcons.chat_bubble,
                label: '채팅',
                onTap: () => onTap?.call(1),
              ),
              _NavItem(
                icon: CupertinoIcons.calendar,
                label: '이벤트',
                onTap: () => onTap?.call(2),
              ),
              _NavItem(
                icon: CupertinoIcons.tree,
                label: '대나무숲',
                onTap: () => onTap?.call(3),
              ),
              _NavItem(
                icon: CupertinoIcons.person,
                label: '내 페이지',
                onTap: () => onTap?.call(4),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback? onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    this.isActive = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: onTap,
      child: SizedBox(
        width: 48,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 24,
              color: isActive ? _AppColors.primary : _AppColors.gray400,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 10,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                color: isActive ? _AppColors.primary : _AppColors.gray400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
