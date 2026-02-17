// =============================================================================
// 대나무숲(커뮤니티) 게시글 작성 화면
// 경로: lib/features/community/screens/post_write_screen.dart
//
// 디자인: 감정 선택 칩, Glassmorphism TextArea, 익명성 강조
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui';
import 'dart:math' as math;

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF0428B);
  static const Color backgroundLight = Color(0xFFF8F6F7);
  // Theme colors based on HTML example
  static const Color gradientStart = Color(0xFFFFF0F5); // pink-50/80
  static const Color gradientEnd = Color(0xFFF8F6F7); // background-light

  static const Color textMain = Color(0xFF181114);
}

// =============================================================================
// 메인 화면
// =============================================================================
class PostWriteScreen extends StatefulWidget {
  const PostWriteScreen({super.key});

  @override
  State<PostWriteScreen> createState() => _PostWriteScreenState();
}

class _PostWriteScreenState extends State<PostWriteScreen> {
  final TextEditingController _textController = TextEditingController();
  final int _maxLength = 300;
  String _currentText = '';

  // 감정 태그 리스트
  final List<String> _emotions = ['#두근두근', '#첫미팅', '#짝사랑', '#비밀', '#설렘', '#고민'];
  String _selectedEmotion = '#두근두근';

  @override
  void initState() {
    super.initState();
    _textController.addListener(() {
      setState(() {
        _currentText = _textController.text;
      });
    });
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: Stack(
        children: [
          // 1. 배경 (Gradient & Abstract Blobs)
          const _BackgroundDecoration(),

          // 2. 메인 컨텐츠
          SafeArea(
            child: Column(
              children: [
                // 헤더
                _Header(
                  onClose: () => Navigator.of(context).pop(),
                  onDraft: () {
                    // TODO: 임시저장 기능
                    HapticFeedback.lightImpact();
                  },
                ),

                // 스크롤 영역
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 감정 선택 섹션
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 24),
                          child: Text(
                            '어떤 마음인가요?',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: _AppColors.textMain,
                              height: 1.2,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // 감정 칩 리스트
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          physics: const BouncingScrollPhysics(),
                          padding: const EdgeInsets.symmetric(horizontal: 24),
                          child: Row(
                            children: _emotions.map((emotion) {
                              final isSelected = _selectedEmotion == emotion;
                              return Padding(
                                padding: const EdgeInsets.only(right: 12),
                                child: GestureDetector(
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    setState(() => _selectedEmotion = emotion);
                                  },
                                  child: AnimatedContainer(
                                    duration: const Duration(milliseconds: 200),
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                      vertical: 10,
                                    ),
                                    decoration: BoxDecoration(
                                      color: isSelected
                                          ? _AppColors.primary
                                          : Colors.white,
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(
                                        color: isSelected
                                            ? Colors.transparent
                                            : Colors.grey.withValues(
                                                alpha: 0.2,
                                              ),
                                      ),
                                      boxShadow: isSelected
                                          ? [
                                              BoxShadow(
                                                color: _AppColors.primary
                                                    .withValues(alpha: 0.3),
                                                blurRadius: 8,
                                                offset: const Offset(0, 4),
                                              ),
                                            ]
                                          : [],
                                    ),
                                    child: Text(
                                      emotion,
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: isSelected
                                            ? FontWeight.bold
                                            : FontWeight.w500,
                                        color: isSelected
                                            ? Colors.white
                                            : Colors.grey[600],
                                        letterSpacing: -0.2,
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                        ),

                        const SizedBox(height: 24),

                        // 입력 폼 (Glass Panel)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(24),
                            child: BackdropFilter(
                              filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                              child: Container(
                                constraints: const BoxConstraints(
                                  minHeight: 300,
                                ),
                                padding: const EdgeInsets.all(24),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.7),
                                  borderRadius: BorderRadius.circular(24),
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.5),
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(
                                        alpha: 0.05,
                                      ),
                                      blurRadius: 16,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  children: [
                                    TextField(
                                      controller: _textController,
                                      maxLines: null,
                                      minLines: 8,
                                      maxLength: _maxLength,
                                      decoration: const InputDecoration(
                                        hintText:
                                            '솔직한 마음을 익명으로 남겨보세요...\n아무도 모를 거예요.',
                                        hintStyle: TextStyle(
                                          color: Colors.grey,
                                          height: 1.6,
                                          fontSize: 16,
                                        ),
                                        border: InputBorder.none,
                                        counterText: '', // 기본 카운터 숨김
                                        contentPadding: EdgeInsets.zero,
                                      ),
                                      style: const TextStyle(
                                        fontSize: 16,
                                        height: 1.6,
                                        color: _AppColors.textMain,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),

                                    const SizedBox(height: 16),
                                    Divider(
                                      height: 1,
                                      color: Colors.grey.withValues(alpha: 0.1),
                                    ),
                                    const SizedBox(height: 16),

                                    // 하단 메타 정보 (익명 보장, 글자수)
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Row(
                                          children: [
                                            Icon(
                                              Icons.lock_outline_rounded,
                                              size: 16,
                                              color: Colors.grey[400],
                                            ),
                                            const SizedBox(width: 4),
                                            Text(
                                              '익명 보장',
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: FontWeight.w500,
                                                color: Colors.grey[400],
                                              ),
                                            ),
                                          ],
                                        ),
                                        Text(
                                          '${_currentText.length}/$_maxLength자',
                                          style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w500,
                                            color: Colors.grey[400],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // 하단 등록 버튼
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
                  child: SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: _currentText.isEmpty
                          ? null
                          : () {
                              HapticFeedback.mediumImpact();
                              // TODO: 등록 로직
                              Navigator.of(context).pop();
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _AppColors.primary,
                        disabledBackgroundColor: _AppColors.primary.withValues(
                          alpha: 0.3,
                        ),
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shadowColor: _AppColors.primary.withValues(alpha: 0.3),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Text(
                            '등록하기',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(width: 8),
                          Icon(Icons.send_rounded, size: 20),
                        ],
                      ),
                    ),
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
// 배경 장식
// =============================================================================
class _BackgroundDecoration extends StatelessWidget {
  const _BackgroundDecoration();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Gradient Background
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [_AppColors.gradientStart, _AppColors.gradientEnd],
            ),
          ),
        ),

        // Abstract Blobs
        Positioned(
          top: -50,
          right: -100,
          child: Container(
            width: 500,
            height: 500,
            decoration: BoxDecoration(
              color: _AppColors.primary.withValues(alpha: 0.05),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),
        Positioned(
          bottom: 50,
          left: -80,
          child: Container(
            width: 300,
            height: 300,
            decoration: BoxDecoration(
              color: Colors.purple.withValues(alpha: 0.05),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 60, sigmaY: 60),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),

        // Decorative Icons (Static Petals)
        Positioned(
          top: 100,
          left: 40,
          child: Transform.rotate(
            angle: 12 * math.pi / 180,
            child: Icon(
              Icons.eco_rounded,
              size: 24,
              color: _AppColors.primary.withValues(alpha: 0.1),
            ),
          ),
        ),
        Positioned(
          top: 200,
          right: 60,
          child: Transform.rotate(
            angle: -45 * math.pi / 180,
            child: Icon(
              Icons.eco_rounded,
              size: 20,
              color: _AppColors.primary.withValues(alpha: 0.08),
            ),
          ),
        ),
        Positioned(
          bottom: 250,
          left: 80,
          child: Transform.rotate(
            angle: 90 * math.pi / 180,
            child: Icon(
              Icons.eco_rounded,
              size: 32,
              color: _AppColors.primary.withValues(alpha: 0.05),
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
  final VoidCallback onClose;
  final VoidCallback onDraft;

  const _Header({required this.onClose, required this.onDraft});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            onPressed: () {
              HapticFeedback.lightImpact();
              onClose();
            },
            icon: const Icon(Icons.close_rounded, size: 28),
            style: IconButton.styleFrom(
              foregroundColor: Colors.grey[800],
              backgroundColor: Colors.transparent,
              padding: const EdgeInsets.all(8),
            ),
          ),
          const Text(
            '대나무숲 글쓰기',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: _AppColors.textMain,
            ),
          ),
          TextButton(
            onPressed: onDraft,
            style: TextButton.styleFrom(
              foregroundColor: Colors.grey[500],
              textStyle: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
            child: const Text('임시저장'),
          ),
        ],
      ),
    );
  }
}
