// =============================================================================
// 프로필 카드 화면 (스와이프 카드 + 하단 버튼)
// 경로: lib/features/matching/screens/profile_card_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const ProfileCardScreen()),
// );
// =============================================================================

import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../shared/widgets/seol_swipe_deck.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color backgroundLight = Color(0xFFF9FAFB);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color lavender50 = Color(0xFFF5F3FF);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray300 = Color(0xFFD1D5DB);
  static const Color emerald500 = Color(0xFF10B981);
  static const Color emerald700 = Color(0xFF047857);
  static const Color pink500 = Color(0xFFEC4899);
  static const Color rose500 = Color(0xFFF43F5E);
}

// =============================================================================
// 프로필 모델
// =============================================================================
class _Profile {
  final String name;
  final int age;
  final String imageUrl;
  final bool isOnline;
  final List<_Tag> tags;

  const _Profile({
    required this.name,
    required this.age,
    required this.imageUrl,
    required this.isOnline,
    required this.tags,
  });
}

class _Tag {
  final IconData icon;
  final String label;

  const _Tag({required this.icon, required this.label});
}

// =============================================================================
// 메인 화면
// =============================================================================
class ProfileCardScreen extends StatefulWidget {
  final VoidCallback? onLike;
  final VoidCallback? onPass;
  final VoidCallback? onShare;

  const ProfileCardScreen({super.key, this.onLike, this.onPass, this.onShare});

  @override
  State<ProfileCardScreen> createState() => _ProfileCardScreenState();
}

class _ProfileCardScreenState extends State<ProfileCardScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  final _deckController = SeolSwipeDeckController();

  static const _profiles = [
    _Profile(
      name: '민지',
      age: 24,
      imageUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAgFO0PnOcP3DRjRkR-qVvcPspw9zwcuy5yZ9DGSltERflpy154Tbi4Z1xEKcsSRSBWH8nyvdsjphQYDlv2EoYdlXp1emQrffYTYPa7a0MnH8emVIBZdeP7b_pErBgqzoEb5UcmLHJiBf-JaeY6vMo4SGrawsUrGI6ts-E7Br34eo81Fj4F9b5g8eVTP4U9p_OzV1tpi03JlIni6xXpR-V1UBHZh9ewHQLYxTE400Q_LZA-lemFSQYCWnDNFxGc55_mI8pwrRFZafA',
      isOnline: true,
      tags: [
        _Tag(icon: CupertinoIcons.drop, label: '혼술할 정도로 좋아하는 편'),
        _Tag(icon: CupertinoIcons.nosign, label: '비흡연'),
        _Tag(icon: CupertinoIcons.sportscourt, label: '매일'),
        _Tag(icon: CupertinoIcons.paw, label: '고양이'),
      ],
    ),
    _Profile(
      name: '수진',
      age: 23,
      imageUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuA-iKoOfd7mUBhLCu8omhZBXx588zQSVaTuUyPxd8tn5HGIqbofexG6xV_wpU-m1DwzanC-9eZa9On_1heZiGjjrRZfW2q-4u5XMCegZ3-FWSb_vFcW2Q-ekVQFZTaKtT8ja--_6YV71R2iJjLA0J91Y1Jnp0SbXNEjmIBvH9TIoHyXY-ErSnUZaRjEhcBVmhOpChRqBrF0r5YpiKtqSi8G8DdMop8R7kiJGLKFoChyCmRyqHE7EB-Km7q6kjBctextaAUtbZwKHDEX',
      isOnline: false,
      tags: [
        _Tag(icon: CupertinoIcons.music_note_2, label: '인디 음악'),
        _Tag(icon: CupertinoIcons.film, label: '영화 감상'),
        _Tag(icon: CupertinoIcons.book, label: '독서'),
      ],
    ),
    _Profile(
      name: '하은',
      age: 22,
      imageUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCZm5OPNQsqWRtn9Q9JRanlA3wGHr2RQpXGWBvXeoJPFMH3ceEkM35k27hOD-SdpW-emSzqFGV1iNHDuvl2-JwD7CohYcY2aC2QMqSvZs2v8obekQXSOa0AJVb9LaO0VT1Gl6rJSMo96FU8_eRYPWNo3_aDOGfEqgjj4W95XZEZIKHfzf_tQda6Qz5X-cE4oBscYXjQeAILJRSjk-xOWqPKxhKKb4_R1kiCzG_BqnVtDKzzdrAYqaJ03uY7RMGrxLqF03aL5KJQgqS_',
      isOnline: true,
      tags: [
        _Tag(icon: CupertinoIcons.airplane, label: '여행 좋아해요'),
        _Tag(icon: CupertinoIcons.camera, label: '사진 찍기'),
        _Tag(icon: CupertinoIcons.heart, label: '강아지'),
      ],
    ),
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(seconds: 1),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _deckController.dispose();
    super.dispose();
  }

  void _onSwiped(int index, SwipeDirection direction) {
    if (direction == SwipeDirection.right) {
      widget.onLike?.call();
    } else {
      widget.onPass?.call();
    }
  }

  void _onLike() {
    HapticFeedback.mediumImpact();
    _deckController.swipeRight();
  }

  void _onPass() {
    HapticFeedback.lightImpact();
    _deckController.swipeLeft();
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: Column(
        children: [
          // 프로필 카드 스와이프 덱
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [_AppColors.lavender50, _AppColors.surfaceLight],
                ),
              ),
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: SeolSwipeDeck(
                    controller: _deckController,
                    onSwiped: _onSwiped,
                    cards: _profiles
                        .map(
                          (p) => _ProfileCard(
                            profile: p,
                            pulseController: _pulseController,
                            onShare: widget.onShare,
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
            ),
          ),
          // 하단 액션 버튼
          Container(
            padding: EdgeInsets.fromLTRB(32, 16, 32, bottomPadding + 40),
            color: _AppColors.surfaceLight,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Pass 버튼
                _ActionButton(
                  icon: CupertinoIcons.xmark,
                  iconColor: _AppColors.gray300,
                  hoverColor: _AppColors.rose500,
                  onPressed: _onPass,
                ),
                const SizedBox(width: 40),
                // Like 버튼
                _ActionButton(
                  icon: CupertinoIcons.heart_fill,
                  iconColor: _AppColors.pink500,
                  hoverColor: _AppColors.pink500,
                  onPressed: _onLike,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 프로필 카드
// =============================================================================
class _ProfileCard extends StatelessWidget {
  final _Profile profile;
  final AnimationController pulseController;
  final VoidCallback? onShare;

  const _ProfileCard({
    required this.profile,
    required this.pulseController,
    this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: CupertinoColors.black,
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: CupertinoColors.black.withValues(alpha: 0.15),
            blurRadius: 25,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(32),
        child: Stack(
          children: [
            // 배경 이미지
            Positioned.fill(
              child: Image.network(
                profile.imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) =>
                    Container(color: _AppColors.gray300),
              ),
            ),
            // 그라데이션 오버레이
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      CupertinoColors.black.withValues(alpha: 0.05),
                      CupertinoColors.black.withValues(alpha: 0),
                      CupertinoColors.black.withValues(alpha: 0.1),
                      CupertinoColors.black.withValues(alpha: 0.6),
                      CupertinoColors.black.withValues(alpha: 0.95),
                    ],
                    stops: const [0.0, 0.25, 0.5, 0.75, 1.0],
                  ),
                ),
              ),
            ),
            // 상단 인디케이터
            Positioned(
              top: 20,
              left: 20,
              right: 20,
              child: Row(
                children: [
                  Expanded(
                    child: Container(
                      height: 4,
                      decoration: BoxDecoration(
                        color: CupertinoColors.white,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Container(
                      height: 4,
                      decoration: BoxDecoration(
                        color: CupertinoColors.white.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Container(
                      height: 4,
                      decoration: BoxDecoration(
                        color: CupertinoColors.white.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // 하단 콘텐츠
            Positioned(
              left: 20,
              right: 20,
              bottom: 24,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 접속 중 배지
                  if (profile.isOnline)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: CupertinoColors.white.withValues(alpha: 0.95),
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: CupertinoColors.black.withValues(alpha: 0.1),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          AnimatedBuilder(
                            animation: pulseController,
                            builder: (_, child) {
                              final opacity =
                                  0.5 + (0.5 * pulseController.value);
                              return Opacity(opacity: opacity, child: child);
                            },
                            child: Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: _AppColors.emerald500,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            '접속 중',
                            style: TextStyle(
                              fontFamily: '.SF Pro Text',
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: _AppColors.emerald700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  // 이름 & 나이 & 공유 버튼
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text(
                            profile.name,
                            style: const TextStyle(
                              fontFamily: '.SF Pro Display',
                              fontSize: 32,
                              fontWeight: FontWeight.w700,
                              color: CupertinoColors.white,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${profile.age}',
                            style: TextStyle(
                              fontFamily: '.SF Pro Display',
                              fontSize: 24,
                              fontWeight: FontWeight.w300,
                              color: CupertinoColors.white.withValues(
                                alpha: 0.95,
                              ),
                            ),
                          ),
                        ],
                      ),
                      CupertinoButton(
                        padding: EdgeInsets.zero,
                        onPressed: onShare,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(20),
                          child: BackdropFilter(
                            filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: CupertinoColors.black.withValues(
                                  alpha: 0.2,
                                ),
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: CupertinoColors.white.withValues(
                                    alpha: 0.2,
                                  ),
                                ),
                              ),
                              child: const Icon(
                                CupertinoIcons.share,
                                size: 20,
                                color: CupertinoColors.white,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // 라벨
                  Row(
                    children: [
                      Icon(
                        CupertinoIcons.tag,
                        size: 14,
                        color: CupertinoColors.white.withValues(alpha: 0.9),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '기본 정보 및 라이프스타일',
                        style: TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          letterSpacing: 0.5,
                          color: CupertinoColors.white.withValues(alpha: 0.9),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // 태그들
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: profile.tags.map((tag) {
                      return ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: CupertinoColors.black.withValues(
                                alpha: 0.5,
                              ),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: CupertinoColors.white.withValues(
                                  alpha: 0.1,
                                ),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  tag.icon,
                                  size: 14,
                                  color: CupertinoColors.white.withValues(
                                    alpha: 0.9,
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  tag.label,
                                  style: const TextStyle(
                                    fontFamily: '.SF Pro Text',
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                    color: CupertinoColors.white,
                                  ),
                                ),
                              ],
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
// 액션 버튼
// =============================================================================
class _ActionButton extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color hoverColor;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.icon,
    required this.iconColor,
    required this.hoverColor,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: onPressed,
      child: Container(
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          shape: BoxShape.circle,
          border: Border.all(color: _AppColors.gray100),
          boxShadow: [
            BoxShadow(
              color: CupertinoColors.black.withValues(alpha: 0.08),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Center(child: Icon(icon, size: 36, color: iconColor)),
      ),
    );
  }
}
