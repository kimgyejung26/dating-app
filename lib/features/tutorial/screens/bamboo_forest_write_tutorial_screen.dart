// =============================================================================
// 대나무숲 튜토리얼 (Write V1) 화면
// 경로: lib/features/tutorial/screens/bamboo_forest_write_tutorial_screen.dart
//
// 디자인: 대나무숲 메인 화면 + 글쓰기 팝업 애니메이션 + FAB 하이라이트
// =============================================================================

import 'package:flutter/material.dart';
import 'dart:ui';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF43F85); // Hot pink
  static const Color backgroundLight = Color(0xFFFFF0F5);
  static const Color textMain = Color(0xFF1F2937);
  static const Color textSub = Color(0xFF6B7280);
}

// =============================================================================
// 메인 화면
// =============================================================================
class BambooForestWriteTutorialScreen extends StatefulWidget {
  const BambooForestWriteTutorialScreen({super.key});

  @override
  State<BambooForestWriteTutorialScreen> createState() =>
      _BambooForestWriteTutorialScreenState();
}

class _BambooForestWriteTutorialScreenState
    extends State<BambooForestWriteTutorialScreen>
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
      duration: const Duration(milliseconds: 1000),
    );

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -0.1), // 위에서 아래로
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.5, 1.0, curve: Curves.easeInOut),
      ),
    );

    Future.delayed(const Duration(milliseconds: 200), () {
      if (mounted) {
        _controller.repeat(reverse: true, period: const Duration(seconds: 2));
      }
      _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: Stack(
        children: [
          // 1. 배경 (가짜 대나무숲 스크린)
          const _FakeBambooForestScreen(),

          // 2. 어두운 오버레이
          Positioned.fill(
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 4, sigmaY: 4),
                child: Container(color: Colors.black.withValues(alpha: 0.6)),
              ),
            ),
          ),

          // 3. 모달 시뮬레이션 (위에서 등장)
          Positioned(
            top: MediaQuery.of(context).size.height * 0.15, // 화면 상단부
            left: 24,
            right: 24,
            child: SlideTransition(
              position: _slideAnimation,
              child: FadeTransition(
                opacity: _fadeAnimation,
                child: const _SimulatedWriteModal(),
              ),
            ),
          ),

          // 4. 하단 튜토리얼 텍스트
          Positioned(
            left: 0,
            right: 0,
            bottom: 160,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: Column(
                children: [
                  const Text(
                    '글쓰기',
                    style: TextStyle(
                      fontFamily: 'Noto Sans KR',
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '익명으로 글을 쓸 수 있어요.\n개인정보(연락처/실명)는 올리지 마세요.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Noto Sans KR',
                      fontSize: 14,
                      color: Colors.white.withValues(alpha: 0.8),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text(
                      '4 / 6',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 5. FAB 하이라이트 (제자리, 실제 버튼 위치 추정)
          Positioned(
            bottom: 100, // Bottom Nav 위
            right: 24,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: ScaleTransition(
                scale: _pulseAnimation,
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: _AppColors.primary.withValues(alpha: 0.5),
                        blurRadius: 30,
                        spreadRadius: 4,
                      ),
                    ],
                  ),
                  child: FloatingActionButton(
                    onPressed: () {
                      // 다음: 대나무숲 안전 튜토리얼
                      Navigator.of(context).pushNamed(RouteNames.bambooForestSafetyTutorial);
                    },
                    backgroundColor: _AppColors.primary,
                    child: const Icon(Icons.edit, color: Colors.white),
                  ),
                ),
              ),
            ),
          ),

          // 6. Tap Here 힌트
          Positioned(
            bottom: 110,
            right: 100,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: Row(
                children: const [
                  Text(
                    'Tap here!',
                    style: TextStyle(
                      fontFamily: 'Caveat', // 손글씨 느낌 (없으면 기본 폰트)
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, color: Colors.white),
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
// 글쓰기 모달 시뮬레이션
// =============================================================================
class _SimulatedWriteModal extends StatelessWidget {
  const _SimulatedWriteModal();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.15),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 모달 헤더
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Icon(Icons.close_rounded, color: _AppColors.textMain),
              const Text(
                '대나무숲 글쓰기',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: _AppColors.textMain,
                ),
              ),
              const Text(
                '임시저장',
                style: TextStyle(fontSize: 14, color: _AppColors.textSub),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 감정 태그
          const Text(
            '어떤 마음인가요?',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _AppColors.textMain,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              _buildTag('#두근두근', isActive: true),
              _buildTag('#첫미팅'),
              _buildTag('#짝사랑'),
            ],
          ),
          const SizedBox(height: 24),

          // 입력창 시뮬레이션
          Container(
            height: 120,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[50], // bg-gray-50
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey[200]!),
            ),
            child: Stack(
              children: [
                const Text(
                  '솔직한 마음을 익명으로 남겨보세요...\n아무도 모를 거예요.',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey,
                    height: 1.5,
                  ),
                ),
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(
                            Icons.lock_outline_rounded,
                            size: 14,
                            color: Colors.grey,
                          ),
                          SizedBox(width: 4),
                          Text(
                            '익명 보장',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                      const Text(
                        '0/300자',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 등록 버튼
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: _AppColors.primary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 4,
                shadowColor: const Color(0xFFFFC2D4), // pink-200 shadow
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  Text(
                    '등록하기',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.send_rounded, size: 18, color: Colors.white),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTag(String label, {bool isActive = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isActive ? _AppColors.primary : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: isActive ? null : Border.all(color: Colors.grey[300]!),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isActive ? Colors.white : _AppColors.textSub,
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

// =============================================================================
// 가짜 대나무숲 스크린 (배경용 - 기존 Intro/Safety와 유사 구조 유지)
// =============================================================================
class _FakeBambooForestScreen extends StatelessWidget {
  const _FakeBambooForestScreen();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Column(
        children: [
          // Header
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Icon(Icons.menu_rounded, color: _AppColors.textMain),
                  const Text(
                    '대나무숲',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFDE8F1), // primary-soft
                      borderRadius: BorderRadius.circular(20),
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

          // Chips
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: const [
                _FakeChip('전체', isActive: true),
                SizedBox(width: 8),
                _FakeChip('인기'),
                SizedBox(width: 8),
                _FakeChip('설렘'),
              ],
            ),
          ),

          // Feed List
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                _FakePostCard(
                  tag: '짝사랑',
                  time: '10 mins ago',
                  content:
                      'Is it weird that I still think about the coffee we had yesterday? I barely slept because my heart was racing so fast.',
                  likes: 24,
                  comments: 5,
                  tagColor: _AppColors.primary,
                ),
                SizedBox(height: 16),
                _FakePostCard(
                  tag: '첫만남',
                  time: '35 mins ago',
                  content:
                      'Meeting someone from the app for the first time in Gangnam tonight. Wish me luck! Does this outfit look okay? 🌸',
                  likes: 156,
                  comments: 32,
                  tagColor: Colors.purple,
                ),
                SizedBox(height: 16),
                _FakePostCard(
                  tag: 'Loading',
                  time: '...',
                  content: '',
                  likes: 0,
                  comments: 0,
                  tagColor: Colors.grey,
                  isLoading: true,
                ),
              ],
            ),
          ),

          // Bottom Nav (Fake)
          Container(
            height: 80,
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFF3F4F6))),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: const [
                Icon(Icons.home_outlined, color: Colors.grey),
                Icon(Icons.forest_rounded, color: _AppColors.primary),
                SizedBox(width: 48), // FAB Space
                Icon(Icons.chat_bubble_outline_rounded, color: Colors.grey),
                Icon(Icons.person_outline_rounded, color: Colors.grey),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FakeChip extends StatelessWidget {
  final String label;
  final bool isActive;
  const _FakeChip(this.label, {this.isActive = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: isActive ? _AppColors.textMain : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: isActive ? null : Border.all(color: Colors.grey[200]!),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: isActive ? Colors.white : _AppColors.textMain,
        ),
      ),
    );
  }
}

class _FakePostCard extends StatelessWidget {
  final String tag;
  final String time;
  final String content;
  final int likes;
  final int comments;
  final Color tagColor;
  final bool isLoading;

  const _FakePostCard({
    required this.tag,
    required this.time,
    required this.content,
    required this.likes,
    required this.comments,
    required this.tagColor,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Container(
        height: 120,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(16),
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: tagColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '[$tag]',
                      style: TextStyle(
                        color: tagColor,
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
              const Icon(Icons.more_horiz, color: Colors.grey, size: 20),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: const TextStyle(
              fontSize: 14,
              height: 1.5,
              color: _AppColors.textMain,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(
                Icons.favorite_rounded,
                size: 16,
                color: tagColor == _AppColors.primary
                    ? Colors.pink[300]
                    : Colors.grey,
              ),
              const SizedBox(width: 4),
              Text(
                '$likes',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              const SizedBox(width: 16),
              const Icon(
                Icons.chat_bubble_rounded,
                size: 16,
                color: Colors.grey,
              ),
              const SizedBox(width: 4),
              Text(
                '$comments',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
