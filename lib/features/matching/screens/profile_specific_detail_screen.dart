// =============================================================================
// AI 매치 추천 프로필 화면
// 경로: lib/features/matching/screens/ai_match_profile_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const AiMatchProfileScreen()),
// );
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFF3E7470);
  static const Color backgroundLight = Color(0xFFF6F7F7);
  static const Color blush = Color(0xFFF6F3F4);
  static const Color cardSurface = Color(0xFFFFFCF7);
  static const Color textMain = Color(0xFF131615);
  static const Color textSub = Color(0xFF6E7C7B);
  static const Color periwinkle = Color(0xFFF4F1FA);
  static const Color gray100 = Color(0xFFF1F5F9);
}

// =============================================================================
// 프로필 모델
// =============================================================================
class _MatchProfile {
  final String name;
  final int age;
  final String university;
  final String major;
  final int matchPercent;
  final String imageUrl;
  final String matchReason;
  final String aboutMe;
  final List<String> interests;

  const _MatchProfile({
    required this.name,
    required this.age,
    required this.university,
    required this.major,
    required this.matchPercent,
    required this.imageUrl,
    required this.matchReason,
    required this.aboutMe,
    required this.interests,
  });
}

// =============================================================================
// 메인 화면
// =============================================================================
class AiMatchProfileScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onMore;
  final VoidCallback? onQna;
  final VoidCallback? onPass;
  final VoidCallback? onLike;
  final VoidCallback? onMessage;

  const AiMatchProfileScreen({
    super.key,
    this.onBack,
    this.onMore,
    this.onQna,
    this.onPass,
    this.onLike,
    this.onMessage,
  });

  static const _profile = _MatchProfile(
    name: 'Jimin',
    age: 22,
    university: 'Seoul National Univ',
    major: 'Visual Design',
    matchPercent: 98,
    imageUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuDaQ9F1J1n9eXSMt0zD11ePZWBZ50QFnse87zfSqcuLDIKtj72KLZDc8huTQTNDkJq5b52jYaAy2jEP7Aa_pwTfw_GbiZt_EHWxfWa5ldYadN8nUVa1apdkpxOnWZLvLoMgVJR4yx7Kdfuh6jghnn7-lrSCOwOhaWZelP_wEuZLWafw-1ZR3ael3gT1mIho0VYC8jhTdljALX8h7KLK-ifrOdmcAZqF9CFM1ui7cfSGPZM4QF5zvguy4c-a2M6i482QkTyu-A9CsxKJ',
    matchReason:
        'Ideally matched for your shared love of quiet study spots and indie music scenes. You both value deep conversations over small talk.',
    aboutMe:
        'I love cafe hopping around campus and finding hidden indie music gems. On weekends, you can usually find me sketching at a quiet library or exploring new art exhibitions in Hongdae. Looking for someone to study with! ☕️🎧',
    interests: [
      '🎨 Visual Arts',
      '🎧 Indie Music',
      '🍵 Matcha Latte',
      '📸 Photography',
      '📚 Library Dates',
    ],
  );

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.blush,
      navigationBar: CupertinoNavigationBar(
        backgroundColor: _AppColors.blush.withValues(alpha: 0.9),
        border: null,
        leading: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: () {
            HapticFeedback.lightImpact();
            if (onBack != null) {
              onBack!();
            } else {
              Navigator.of(context, rootNavigator: true).pop();
            }
          },
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: CupertinoColors.black.withValues(alpha: 0.05),
            ),
            child: const Icon(
              CupertinoIcons.chevron_down,
              size: 28,
              color: _AppColors.textMain,
            ),
          ),
        ),
        middle: Text(
          'AI MATCH',
          style: TextStyle(
            fontFamily: '.SF Pro Text',
            fontSize: 14,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
            color: _AppColors.primary.withValues(alpha: 0.8),
          ),
        ),
        trailing: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: onMore,
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: CupertinoColors.black.withValues(alpha: 0.05),
            ),
            child: const Icon(
              CupertinoIcons.ellipsis,
              size: 24,
              color: _AppColors.textMain,
            ),
          ),
        ),
      ),
      child: Stack(
        children: [
          // 메인 콘텐츠
          SafeArea(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: EdgeInsets.fromLTRB(16, 16, 16, bottomPadding + 140),
              child: _ProfileCard(profile: _profile),
            ),
          ),
          // 하단 액션 바
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _BottomActionBar(
              bottomPadding: bottomPadding,
              onQna: onQna,
              onPass: onPass,
              onLike: onLike,
              onMessage: onMessage,
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
  final _MatchProfile profile;

  const _ProfileCard({required this.profile});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _AppColors.cardSurface,
        borderRadius: BorderRadius.circular(40),
        boxShadow: [
          BoxShadow(
            color: _AppColors.primary.withValues(alpha: 0.1),
            blurRadius: 40,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 히어로 이미지
          _HeroImage(
            imageUrl: profile.imageUrl,
            matchPercent: profile.matchPercent,
          ),
          // 카드 콘텐츠
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 40),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 아이덴티티
                Text(
                  '${profile.name}, ${profile.age}',
                  style: const TextStyle(
                    fontFamily: '.SF Pro Display',
                    fontSize: 36,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.5,
                    color: _AppColors.textMain,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(
                      CupertinoIcons.building_2_fill,
                      size: 18,
                      color: _AppColors.textSub,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '${profile.university} • ${profile.major}',
                      style: const TextStyle(
                        fontFamily: '.SF Pro Text',
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: _AppColors.textSub,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                // AI 인사이트 박스
                _AiInsightBox(reason: profile.matchReason),
                const SizedBox(height: 32),
                // About Me
                const Text(
                  'About Me',
                  style: TextStyle(
                    fontFamily: '.SF Pro Display',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: _AppColors.textMain,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  profile.aboutMe,
                  style: const TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 17,
                    height: 1.7,
                    color: _AppColors.textSub,
                  ),
                ),
                const SizedBox(height: 32),
                // Interests
                const Text(
                  'Interests',
                  style: TextStyle(
                    fontFamily: '.SF Pro Display',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: _AppColors.textMain,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: profile.interests.map((interest) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: _AppColors.backgroundLight,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: _AppColors.gray100),
                      ),
                      child: Text(
                        interest,
                        style: const TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: _AppColors.textMain,
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
    );
  }
}

// =============================================================================
// 히어로 이미지
// =============================================================================
class _HeroImage extends StatelessWidget {
  final String imageUrl;
  final int matchPercent;

  const _HeroImage({required this.imageUrl, required this.matchPercent});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 480,
      width: double.infinity,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // 이미지
          Image.network(
            imageUrl,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(color: _AppColors.gray100),
          ),
          // 그라데이션
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            height: 200,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    _AppColors.cardSurface.withValues(alpha: 0),
                    _AppColors.cardSurface.withValues(alpha: 0.9),
                  ],
                ),
              ),
            ),
          ),
          // 매치 배지
          Positioned(
            left: 24,
            bottom: 24,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: CupertinoColors.white.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: CupertinoColors.white.withValues(alpha: 0.2),
                ),
                boxShadow: [
                  BoxShadow(
                    color: CupertinoColors.black.withValues(alpha: 0.05),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    CupertinoIcons.sparkles,
                    size: 18,
                    color: _AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '$matchPercent% Match',
                    style: const TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
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
}

// =============================================================================
// AI 인사이트 박스
// =============================================================================
class _AiInsightBox extends StatelessWidget {
  final String reason;

  const _AiInsightBox({required this.reason});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.periwinkle.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _AppColors.periwinkle),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: CupertinoColors.white,
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: CupertinoColors.black.withValues(alpha: 0.05),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: const Icon(
              CupertinoIcons.lightbulb,
              size: 20,
              color: _AppColors.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Why you match',
                  style: TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: _AppColors.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  reason,
                  style: const TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 14,
                    height: 1.5,
                    color: _AppColors.textMain,
                  ),
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
// 하단 액션 바
// =============================================================================
class _BottomActionBar extends StatelessWidget {
  final double bottomPadding;
  final VoidCallback? onQna;
  final VoidCallback? onPass;
  final VoidCallback? onLike;
  final VoidCallback? onMessage;

  const _BottomActionBar({
    required this.bottomPadding,
    this.onQna,
    this.onPass,
    this.onLike,
    this.onMessage,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(24, 16, 24, bottomPadding + 24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _AppColors.blush.withValues(alpha: 0),
            _AppColors.blush.withValues(alpha: 0.95),
            _AppColors.blush,
          ],
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Q&A 버튼
          _ActionButton(
            icon: CupertinoIcons.chat_bubble_text,
            size: 56,
            iconSize: 26,
            isSecondary: true,
            onPressed: onQna,
          ),
          // Pass 버튼
          _ActionButton(
            icon: CupertinoIcons.xmark,
            size: 64,
            iconSize: 32,
            isSecondary: true,
            onPressed: onPass,
          ),
          // Like 버튼 (메인)
          _ActionButton(
            icon: CupertinoIcons.heart_fill,
            size: 80,
            iconSize: 40,
            isPrimary: true,
            onPressed: onLike,
          ),
          // Message 버튼
          _ActionButton(
            icon: CupertinoIcons.paperplane_fill,
            size: 56,
            iconSize: 26,
            isSecondary: true,
            onPressed: onMessage,
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final double size;
  final double iconSize;
  final bool isPrimary;
  final bool isSecondary;
  final VoidCallback? onPressed;

  const _ActionButton({
    required this.icon,
    required this.size,
    required this.iconSize,
    this.isPrimary = false,
    this.isSecondary = false,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: () {
        HapticFeedback.mediumImpact();
        onPressed?.call();
      },
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isPrimary ? _AppColors.primary : CupertinoColors.white,
          border: isSecondary ? Border.all(color: _AppColors.gray100) : null,
          boxShadow: [
            BoxShadow(
              color: isPrimary
                  ? _AppColors.primary.withValues(alpha: 0.3)
                  : CupertinoColors.black.withValues(alpha: 0.08),
              blurRadius: isPrimary ? 20 : 12,
              offset: Offset(0, isPrimary ? 8 : 4),
            ),
          ],
        ),
        child: Icon(
          icon,
          size: iconSize,
          color: isPrimary ? CupertinoColors.white : _AppColors.textSub,
        ),
      ),
    );
  }
}
