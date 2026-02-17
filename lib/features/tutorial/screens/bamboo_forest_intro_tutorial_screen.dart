// =============================================================================
// 대나무숲 튜토리얼 (Intro V1) 화면
// 경로: lib/features/tutorial/screens/bamboo_forest_intro_tutorial_screen.dart
//
// 디자인: 대나무숲 메인 화면 시뮬레이션 + 스포트라이트 오버레이 + 튜토리얼 모달
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'dart:ui';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF43F85); // Hot pink
  static const Color backgroundLight = Color(0xFFFDF2F8); // Lavender/Pink tint
  static const Color textMain = Color(0xFF1F2937);
}

// =============================================================================
// 메인 화면
// =============================================================================
class BambooForestIntroTutorialScreen extends StatefulWidget {
  const BambooForestIntroTutorialScreen({super.key});

  @override
  State<BambooForestIntroTutorialScreen> createState() =>
      _BambooForestIntroTutorialScreenState();
}

class _BambooForestIntroTutorialScreenState
    extends State<BambooForestIntroTutorialScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
      ),
    );

    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero).animate(
          CurvedAnimation(
            parent: _controller,
            curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
          ),
        );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.5, 1.0, curve: Curves.easeInOut),
      ),
    );

    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 하단 네비게이션 바의 대나무숲 아이콘 위치 추정 (화면 비율에 따라 조정 필요)
    // HTML CSS: left: 28%, width: 60px
    // Flutter: Align or Positioned relative to screen width
    final screenWidth = MediaQuery.of(context).size.width;
    final spotlightCenter = Offset(
      screenWidth * 0.35,
      MediaQuery.of(context).size.height - 80,
    ); // 대략적인 위치

    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: Stack(
        children: [
          // 1. 배경 (대나무숲 메인 화면 시뮬레이션)
          const _FakeBambooForestScreen(),

          // 2. 어두운 오버레이 + 스포트라이트 (CustomPainter)
          Positioned.fill(
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: CustomPaint(
                painter: _SpotlightPainter(
                  spotlightCenter: spotlightCenter,
                  spotlightRadius: 35,
                ),
              ),
            ),
          ),

          // 3. 하이라이트 링 애니메이션
          Positioned(
            left: spotlightCenter.dx - 35,
            top: spotlightCenter.dy - 35,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: ScaleTransition(
                scale: _pulseAnimation,
                child: Container(
                  width: 70,
                  height: 70,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: _AppColors.primary.withValues(alpha: 0.8),
                      width: 2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: _AppColors.primary.withValues(alpha: 0.5),
                        blurRadius: 15,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // 4. 튜토리얼 컨텐츠 (상단 모달 & 하단 컨트롤)
          SafeArea(
            child: Column(
              children: [
                // Skip 버튼
                Padding(
                  padding: const EdgeInsets.only(top: 16, right: 24),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(
                        'Skip',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 60),

                // 중앙 모달 (환영 메시지)
                SlideTransition(
                  position: _slideAnimation,
                  child: FadeTransition(
                    opacity: _fadeAnimation,
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 32),
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.2),
                        ),
                      ),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                        child: Column(
                          children: [
                            const Text(
                              '대나무숲에 오신걸\n환영해요! 🎋',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontFamily: 'Noto Sans KR',
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                                height: 1.3,
                              ),
                            ),
                            const SizedBox(height: 12),
                            RichText(
                              textAlign: TextAlign.center,
                              text: TextSpan(
                                style: TextStyle(
                                  fontFamily: 'Noto Sans KR',
                                  fontSize: 14,
                                  color: Colors.white.withValues(alpha: 0.8),
                                  height: 1.5,
                                ),
                                children: const [
                                  TextSpan(text: '대나무숲은 익명으로\n'),
                                  TextSpan(text: '연애 썰/고민/성공후기를 나누는\n'),
                                  TextSpan(
                                    text: '비밀스러운 공간',
                                    style: TextStyle(
                                      color: _AppColors.primary,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  TextSpan(text: '이에요.'),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                const Spacer(),

                // 하단 인디케이터 화살표
                FadeTransition(
                  opacity: _fadeAnimation,
                  child: const Icon(
                    Icons.keyboard_arrow_down_rounded,
                    color: Colors.white54,
                    size: 40,
                  ),
                ),

                const SizedBox(height: 20),

                // 하단 버튼 영역
                Padding(
                  padding: const EdgeInsets.only(
                    left: 24,
                    right: 24,
                    bottom: 40,
                  ),
                  child: Column(
                    children: [
                      // 인디케이터 닷 (1/6)
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _buildDot(active: true),
                          _buildDot(),
                          _buildDot(),
                          _buildDot(),
                          _buildDot(),
                          _buildDot(),
                        ],
                      ),
                      const SizedBox(height: 24),
                      // '다음으로' 버튼
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: CupertinoButton(
                          color: _AppColors.primary,
                          padding: EdgeInsets.zero,
                          borderRadius: BorderRadius.circular(16),
                          onPressed: () {
                            Navigator.of(context).pushNamed(RouteNames.bambooForestWriteTutorial);
                          },
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: const [
                              Text(
                                '다음으로',
                                style: TextStyle(
                                  fontFamily: 'Noto Sans KR',
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              SizedBox(width: 8),
                              Icon(
                                Icons.arrow_forward_rounded,
                                color: Colors.white,
                                size: 18,
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      // 페이지 번호 텍스트
                      Text(
                        '1 / 6',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.4),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 2.0,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDot({bool active = false}) {
    return Container(
      width: 8,
      height: 8,
      margin: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: active
            ? _AppColors.primary
            : Colors.white.withValues(alpha: 0.3),
        shape: BoxShape.circle,
      ),
    );
  }
}

// =============================================================================
// 스포트라이트 Painter
// =============================================================================
class _SpotlightPainter extends CustomPainter {
  final Offset spotlightCenter;
  final double spotlightRadius;

  _SpotlightPainter({
    required this.spotlightCenter,
    required this.spotlightRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color.fromRGBO(24, 24, 27, 0.8); // Zinc-900 80%

    // 전체 화면 경로
    final backgroundPath = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height));

    // 스포트라이트 구멍 경로
    final spotlightPath = Path()
      ..addOval(
        Rect.fromCircle(center: spotlightCenter, radius: spotlightRadius),
      );

    // 차집합 (구멍 뚫기)
    final path = Path.combine(
      PathOperation.difference,
      backgroundPath,
      spotlightPath,
    );

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// =============================================================================
// 가짜 대나무숲 화면 (배경용)
// =============================================================================
class _FakeBambooForestScreen extends StatelessWidget {
  const _FakeBambooForestScreen();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Column(
        children: [
          // 헤더
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Icon(
                    Icons.menu_rounded,
                    size: 28,
                    color: Colors.black87,
                  ),
                  const Text(
                    '대나무숲',
                    style: TextStyle(
                      fontFamily: 'Noto Sans KR',
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: _AppColors.textMain,
                    ),
                  ),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: _AppColors.primary.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.edit_rounded,
                      color: _AppColors.primary,
                      size: 20,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 칩 리스트
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              children: [
                _buildChip('전체', isSelected: true),
                const SizedBox(width: 8),
                _buildChip('인기'),
                const SizedBox(width: 8),
                _buildChip('설렘'),
              ],
            ),
          ),

          // 피드 리스트 (흐릿하게 처리)
          Expanded(
            child: Opacity(
              opacity: 0.4,
              child: ListView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 8,
                ),
                children: [
                  _buildPostCard(
                    category: '짝사랑',
                    time: '10 mins ago',
                    content:
                        'Is it weird that I still think about the coffee we had yesterday? I barely slept because my heart was racing so fast.',
                    likes: 24,
                    comments: 5,
                    color: Colors.pink,
                  ),
                  const SizedBox(height: 16),
                  _buildPostCard(
                    category: '첫만남',
                    time: '35 mins ago',
                    content:
                        'Meeting someone from the app for the first time in Gangnam tonight. Wish me luck!',
                    likes: 156,
                    comments: 32,
                    color: Colors.purple,
                  ),
                ],
              ),
            ),
          ),

          // 하단 바 (Fake)
          Container(
            height: 80,
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFF3F4F6))),
            ),
            padding: const EdgeInsets.only(bottom: 20),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: const [
                Icon(Icons.home_outlined, color: Colors.grey),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.forest_rounded, color: _AppColors.primary),
                    Text(
                      'Bamboo',
                      style: TextStyle(
                        fontSize: 10,
                        color: _AppColors.primary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                // 가운데 FAB 자리
                SizedBox(width: 40),
                Icon(Icons.chat_bubble_outline_rounded, color: Colors.grey),
                Icon(Icons.person_outline_rounded, color: Colors.grey),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChip(String label, {bool isSelected = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected ? Colors.black : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: isSelected ? null : Border.all(color: Colors.grey[300]!),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? Colors.white : Colors.grey[600],
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildPostCard({
    required String category,
    required String time,
    required String content,
    required int likes,
    required int comments,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey[100]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '[$category]',
                  style: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                time,
                style: const TextStyle(color: Colors.grey, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: const TextStyle(
              fontSize: 14,
              color: Color(0xFF1F2937),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(Icons.favorite_rounded, color: Colors.pink[300], size: 16),
              const SizedBox(width: 4),
              Text(
                '$likes',
                style: const TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(width: 16),
              const Icon(
                Icons.chat_bubble_rounded,
                color: Colors.grey,
                size: 16,
              ),
              const SizedBox(width: 4),
              Text(
                '$comments',
                style: const TextStyle(color: Colors.grey, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
