// =============================================================================
// 3:3 매칭 결과 화면 (상대 팀 공개 화면)
// 경로: lib/features/event/screens/three_vs_three_match_screen.dart
//
// HTML to Flutter 변환 구현
// - Cupertino 스타일 적용
// - 상대 팀(토끼) vs 우리 팀(여우) 그리드 배치
// - 중앙 하트 펄스 애니메이션
// - 카드 그라데이션 및 스타일링
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart' show Colors, Icons;

// =============================================================================
// 색상 정의
// =============================================================================
class _AppColors {
  static const Color primary = Color(
    0xFFFF5A78,
  ); // #FF5A78 (Sophisticated Pink)
  static const Color backgroundLight = Color(0xFFF9FAFB); // Very light gray
  static const Color surfaceLight = CupertinoColors.white;
  static const Color textMain = Color(0xFF111827); // gray-900 equivalent
  static const Color textSub = Color(0xFF6B7280); // gray-500 equivalent
  static const Color textGray800 = Color(0xFF1F2937);

  // 상대 팀 그라데이션 (토끼)
  static const Color rabbitBlue1 = Color(0xFFDBEAFE); // blue-100
  static const Color rabbitBlue2 = Color(0xFFBFDBFE); // blue-200
  static const Color rabbitPurple1 = Color(0xFFF3E8FF); // purple-100
  static const Color rabbitPurple2 = Color(0xFFE9D5FF); // purple-200
  static const Color rabbitIndigo1 = Color(0xFFE0E7FF); // indigo-100
  static const Color rabbitIndigo2 = Color(0xFFC7D2FE); // indigo-200

  // 우리 팀 그라데이션 (여우)
  static const Color foxOrange1 = Color(0xFFFFEDD5); // orange-100
  static const Color foxAmber1 = Color(0xFFFEF3C7); // amber-100
  static const Color foxRed1 = Color(0xFFFEE2E2); // red-100
}

// =============================================================================
// 메인 화면
// =============================================================================
class ThreeVsThreeMatchScreen extends StatelessWidget {
  const ThreeVsThreeMatchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            Column(
              children: [
                // 헤더
                _Header(onBack: () => Navigator.of(context).pop()),

                // 메인 스크롤 영역
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.only(
                      left: 20,
                      right: 20,
                      top: 24,
                      bottom: 100,
                    ),
                    child: Column(
                      children: const [
                        // 상대 팀 섹션
                        _OpponentTeamSection(),

                        // 중앙 하트 애니메이션
                        _HeartPulseAnimation(),

                        // 우리 팀 섹션
                        _MyTeamSection(),

                        // 하단 여백 확보
                        SizedBox(height: 80),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            // 하단 고정 버튼
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: const _BottomActionBar(),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final VoidCallback onBack;

  const _Header({required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      decoration: BoxDecoration(
        color: _AppColors.surfaceLight.withValues(alpha: 0.8),
        border: const Border(
          bottom: BorderSide(color: Color(0xFFF3F4F6)), // gray-100
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          CupertinoButton(
            padding: EdgeInsets.zero,
            minimumSize: const Size(40, 40),
            onPressed: onBack,
            child: const Icon(
              Icons.arrow_back,
              color: Color(0xFF1F2937),
              size: 24,
            ),
          ),
          const Text(
            '설레연 3:3 미팅',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: _AppColors.textMain,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(width: 40), // spacer for centering
        ],
      ),
    );
  }
}

// =============================================================================
// 상대 팀 섹션 (토끼)
// =============================================================================
class _OpponentTeamSection extends StatelessWidget {
  const _OpponentTeamSection();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '상대 팀',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: _AppColors.textSub,
                  letterSpacing: 0.5, // tracking-wider
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text(
                  '매칭 완료',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: _AppColors.primary,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: const [
            Expanded(
              child: _AnimalCard(
                name: '토끼 A',
                icon: Icons.cruelty_free,
                iconColor: Color(0xFF60A5FA), // blue-400
                gradientColors: [
                  _AppColors.rabbitBlue1,
                  _AppColors.rabbitBlue2,
                ],
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _AnimalCard(
                name: '토끼 B',
                icon: Icons.cruelty_free,
                iconColor: Color(0xFFC084FC), // purple-400
                gradientColors: [
                  _AppColors.rabbitPurple1,
                  _AppColors.rabbitPurple2,
                ],
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _AnimalCard(
                name: '토끼 C',
                icon: Icons.cruelty_free,
                iconColor: Color(0xFF818CF8), // indigo-400
                gradientColors: [
                  _AppColors.rabbitIndigo1,
                  _AppColors.rabbitIndigo2,
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// =============================================================================
// 동물 카드 (공통 위젯)
// =============================================================================
class _AnimalCard extends StatelessWidget {
  final String name;
  final IconData icon; // Material Icon
  final Color iconColor;
  final List<Color> gradientColors;
  final bool isMyCard; // '나' 카드 여부 (테두리 등 강조)

  const _AnimalCard({
    required this.name,
    required this.icon,
    required this.iconColor,
    required this.gradientColors,
    this.isMyCard = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AspectRatio(
          aspectRatio: 3 / 4,
          child: Container(
            decoration: BoxDecoration(
              color: _AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(24),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x0A000000), // shadow-soft
                  blurRadius: 30,
                  offset: Offset(0, 8),
                ),
              ],
              border: isMyCard
                  ? Border.all(
                      color: _AppColors.primary.withValues(alpha: 0.2),
                      width: 2,
                    )
                  : null,
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Icon Circle
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.bottomLeft,
                      end: Alignment.topRight,
                      colors: gradientColors.length >= 2
                          ? gradientColors
                          : [Colors.grey.shade100, Colors.grey.shade200],
                    ),
                  ),
                  child: Icon(
                    icon,
                    color: isMyCard
                        ? const Color(0xFF9CA3AF)
                        : iconColor.withValues(alpha: 0.8),
                    size: isMyCard ? 30 : 20,
                  ),
                ),

                // My Card Indicator (Bottom Bar)
                if (isMyCard)
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    child: Container(
                      height: 4,
                      color: _AppColors.primary.withValues(alpha: 0.5),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          name,
          style: TextStyle(
            fontSize: isMyCard ? 14 : 12,
            fontWeight: isMyCard ? FontWeight.w700 : FontWeight.w500,
            color: isMyCard
                ? _AppColors.textGray800
                : const Color(0xFF9CA3AF), // gray-400
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 중앙 하트 펄스 애니메이션
// =============================================================================
class _HeartPulseAnimation extends StatefulWidget {
  const _HeartPulseAnimation();

  @override
  State<_HeartPulseAnimation> createState() => _HeartPulseAnimationState();
}

class _HeartPulseAnimationState extends State<_HeartPulseAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 1.2,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 120, // 넉넉한 높이 확보
      alignment: Alignment.center,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 연결선 (Gradient Line)
          Container(
            width: 1,
            height: 80,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  Colors.grey.shade200,
                  Colors.transparent,
                ],
              ),
            ),
          ),

          // 하트 아이콘
          ScaleTransition(
            scale: _scaleAnimation,
            child: Container(
              width: 48,
              height: 48,
              decoration: const BoxDecoration(
                color: _AppColors.surfaceLight,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0x0A000000), // shadow-soft
                    blurRadius: 30,
                    offset: Offset(0, 8),
                  ),
                ],
              ),
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.grey.shade50),
                ),
                child: const Icon(
                  Icons.favorite,
                  color: _AppColors.primary,
                  size: 24,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 우리 팀 섹션 (여우)
// =============================================================================
class _MyTeamSection extends StatelessWidget {
  const _MyTeamSection();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 4, vertical: 8),
          child: Text(
            '우리 팀',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: _AppColors.textSub,
              letterSpacing: 0.5,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: const [
            Expanded(
              child: _AnimalCard(
                name: '나',
                icon: Icons.person,
                iconColor:
                    Colors.grey, // not used due to isMyCard logic but required
                gradientColors: [
                  Color(0xFFF3F4F6),
                  Color(0xFFE5E7EB),
                ], // gray-100, gray-200
                isMyCard: true,
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _AnimalCard(
                name: '여우 A',
                icon: Icons.pets,
                iconColor: Color(0xFFFB923C), // orange-400
                gradientColors: [_AppColors.foxOrange1, _AppColors.foxAmber1],
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _AnimalCard(
                name: '여우 B',
                icon: Icons.pets,
                iconColor: Color(0xFFF59E0B), // amber-500
                gradientColors: [_AppColors.foxAmber1, _AppColors.foxRed1],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// =============================================================================
// 하단 액션 버튼
// =============================================================================
class _BottomActionBar extends StatelessWidget {
  const _BottomActionBar();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Colors.white.withValues(alpha: 0), Colors.white],
          stops: const [0.0, 0.3],
        ),
      ),
      padding: EdgeInsets.fromLTRB(
        24,
        48,
        24,
        MediaQuery.of(context).padding.bottom + 24,
      ),
      child: CupertinoButton(
        padding: EdgeInsets.zero,
        onPressed: () {},
        child: Container(
          width: double.infinity,
          height: 56,
          decoration: BoxDecoration(
            color: _AppColors.primary,
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: _AppColors.primary.withValues(alpha: 0.3),
                blurRadius: 20,
                spreadRadius: 0,
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Text(
                '채팅방 입장하기',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
              SizedBox(width: 8),
              Icon(Icons.chat_bubble_rounded, color: Colors.white, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
