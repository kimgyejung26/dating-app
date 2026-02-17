// =============================================================================
// AI 취향 학습 튜토리얼 화면 (Tutorial 6)
// 경로: lib/features/tutorial/screens/ai_taste_training_tutorial_screen.dart
//
// 디자인: AI 이미지 스와이프 학습 화면 시뮬레이션 + 스와이프 유도 애니메이션
// =============================================================================

import 'package:flutter/material.dart';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF5E8A);
  static const Color secondary = Color(0xFF8B5CF6);
  static const Color backgroundLight = Color(0xFFFFF7FA);

  static const Color textMain = Color(0xFF1F2937);
  static const Color textSub = Color(0xFF6B7280);
}

// =============================================================================
// 메인 화면
// =============================================================================
class AiTasteTrainingTutorialScreen extends StatefulWidget {
  const AiTasteTrainingTutorialScreen({super.key});

  @override
  State<AiTasteTrainingTutorialScreen> createState() =>
      _AiTasteTrainingTutorialScreenState();
}

class _AiTasteTrainingTutorialScreenState
    extends State<AiTasteTrainingTutorialScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _arrowController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _arrowAnimation;

  @override
  void initState() {
    super.initState();

    // 펄스 애니메이션 (중앙 핑거 팁)
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _pulseController.repeat(reverse: true);

    // 화살표 슬라이드 애니메이션
    _arrowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _arrowAnimation = Tween<double>(begin: -8.0, end: 8.0).animate(
      CurvedAnimation(parent: _arrowController, curve: Curves.easeInOut),
    );
    _arrowController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _arrowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: Stack(
        children: [
          // 1. 배경 (가짜 AI 트레이닝 화면)
          const _FakeAiTrainingScreen(),

          // 2. 튜토리얼 오버레이
          Positioned.fill(
            child: Stack(
              alignment: Alignment.center,
              children: [
                // 중앙 스와이프 가이드
                Positioned(
                  top: MediaQuery.of(context).size.height * 0.4, // 카드 위치 추정
                  child: _buildSwipeGuide(),
                ),
              ],
            ),
          ),

          // 3. 튜토리얼 닫기/완료 버튼 (임시 - 화면 터치시 다음으로)
          Positioned.fill(
            child: GestureDetector(
              onTap: () {
                // 다음 튜토리얼: 슬롯머신 튜토리얼
                Navigator.of(context).pushNamed(RouteNames.slotMachineTutorial);
              },
              behavior: HitTestBehavior.translucent,
              child: Container(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSwipeGuide() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 200,
          height: 100,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // 좌측 화살표
              AnimatedBuilder(
                animation: _arrowAnimation,
                builder: (context, child) {
                  return Positioned(
                    left: 20 + _arrowAnimation.value, // 움직임
                    child: Transform.rotate(
                      angle: 3.14, // 180도 회전
                      child: const Icon(
                        Icons.arrow_right_alt_rounded,
                        color: Colors.white,
                        size: 40,
                      ),
                    ),
                  );
                },
              ),

              // 우측 화살표
              AnimatedBuilder(
                animation: _arrowAnimation,
                builder: (context, child) {
                  return Positioned(
                    right: 20 - _arrowAnimation.value, // 반대 움직임
                    child: const Icon(
                      Icons.arrow_right_alt_rounded,
                      color: Colors.white,
                      size: 40,
                    ),
                  );
                },
              ),

              // 중앙 손가락/터치 포인트
              ScaleTransition(
                scale: _pulseAnimation,
                child: Container(
                  width: 50,
                  height: 50,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 2),
                    boxShadow: [
                      BoxShadow(
                        color: _AppColors.primary.withValues(alpha: 0.5),
                        blurRadius: 20,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.touch_app_rounded,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                ),
              ),

              // 좌우 아이콘 (X / Heart) - 페이드
              Positioned(
                left: 0,
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.close_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
              ),
              Positioned(
                right: 0,
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: _AppColors.primary.withValues(alpha: 0.4),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.favorite_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(30),
            border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
          ),
          child: const Text(
            'Swipe left or right',
            style: TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
              letterSpacing: 1.2,
            ),
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 가짜 AI 트레이닝 화면 (배경용)
// =============================================================================
class _FakeAiTrainingScreen extends StatelessWidget {
  const _FakeAiTrainingScreen();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Column(
        children: [
          // 상단 그라데이션 및 헤더
          Container(
            padding: const EdgeInsets.fromLTRB(24, 60, 24, 20), // SafeArea 고려
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: const [
                    Icon(
                      Icons.favorite_rounded,
                      color: _AppColors.primary,
                      size: 24,
                    ),
                    SizedBox(width: 8),
                    Text(
                      '설레연',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: _AppColors.secondary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        children: const [
                          Icon(
                            Icons.auto_awesome,
                            size: 12,
                            color: _AppColors.primary,
                          ),
                          SizedBox(width: 4),
                          Text(
                            'AI 취향',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Stack(
                      children: [
                        const Icon(
                          Icons.notifications_outlined,
                          size: 28,
                          color: Colors.grey,
                        ),
                        Positioned(
                          right: 2,
                          top: 2,
                          child: Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Colors.red,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 타이틀 영역
                  Container(
                    margin: const EdgeInsets.only(bottom: 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          margin: const EdgeInsets.only(bottom: 8),
                          decoration: BoxDecoration(
                            color: _AppColors.secondary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'AI Training',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: _AppColors.secondary,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                        const Text(
                          '스와이프할수록\n추천이 더 정교해져요',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            height: 1.3,
                            color: _AppColors.textMain,
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'AI 이미지 스와이프로 당신의 취향을 학습합니다.',
                          style: TextStyle(
                            fontSize: 14,
                            color: _AppColors.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // 카드 스택 (메인 이미지)
                  Expanded(
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        // 뒤쪽 카드 (Next Profile)
                        Transform.scale(
                          scale: 0.95,
                          child: Container(
                            margin: const EdgeInsets.only(top: 20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(24),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.1),
                                  blurRadius: 20,
                                ),
                              ],
                            ),
                          ),
                        ),
                        // 앞쪽 카드 (Current Profile)
                        Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(24),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.15),
                                blurRadius: 20,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          clipBehavior: Clip.hardEdge,
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              // 이미지 (플레이스홀더)
                              Container(
                                color: Colors.grey[300],
                              ), // 실제 이미지는 네트워크 이미지 사용 권장
                              // 그라데이션 오버레이
                              Container(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.topCenter,
                                    end: Alignment.bottomCenter,
                                    colors: [
                                      Colors.transparent,
                                      Colors.black.withValues(alpha: 0.8),
                                    ],
                                    stops: const [0.6, 1.0],
                                  ),
                                ),
                              ),

                              // 프로필 정보
                              Positioned(
                                left: 20,
                                right: 20,
                                bottom: 24,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        const Text(
                                          'Ji-min',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 28,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 8,
                                            vertical: 2,
                                          ),
                                          decoration: BoxDecoration(
                                            color: Colors.white.withValues(
                                              alpha: 0.2,
                                            ),
                                            borderRadius: BorderRadius.circular(
                                              12,
                                            ),
                                            border: Border.all(
                                              color: Colors.white.withValues(
                                                alpha: 0.3,
                                              ),
                                            ),
                                          ),
                                          child: const Text(
                                            '94% Match',
                                            style: TextStyle(
                                              color: Colors.white,
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      "Business Admin • '01",
                                      style: TextStyle(
                                        color: Colors.white.withValues(
                                          alpha: 0.9,
                                        ),
                                        fontSize: 14,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    const SizedBox(height: 12),
                                    Row(
                                      children: [
                                        _buildTag('TRAVEL'),
                                        const SizedBox(width: 8),
                                        _buildTag('COFFEE'),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),

                  // 하단 Daily Limit
                  Container(
                    margin: const EdgeInsets.only(top: 24, bottom: 24),
                    alignment: Alignment.center,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: Colors.grey[200]!),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.05),
                            blurRadius: 10,
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.bolt_rounded,
                            color: Colors.amber,
                            size: 16,
                          ),
                          const SizedBox(width: 4),
                          RichText(
                            text: TextSpan(
                              style: TextStyle(
                                color: _AppColors.textSub,
                                fontSize: 12,
                              ),
                              children: [
                                const TextSpan(text: 'Daily limit: '),
                                TextSpan(
                                  text: '30',
                                  style: TextStyle(
                                    color: _AppColors.primary,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Bottom Nav (Fake)
          Container(
            height: 80,
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFF3F4F6))),
              boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 20)],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: const [
                Icon(Icons.favorite_rounded, color: _AppColors.primary),
                Icon(Icons.chat_bubble_outline_rounded, color: Colors.grey),
                Icon(Icons.calendar_today_rounded, color: Colors.grey),
                Icon(Icons.forest_outlined, color: Colors.grey),
                Icon(Icons.person_outline_rounded, color: Colors.grey),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTag(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
