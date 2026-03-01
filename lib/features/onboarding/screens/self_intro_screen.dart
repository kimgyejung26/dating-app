// =============================================================================
// 자기소개 입력 화면 (회원가입 5단계)
// 경로: lib/features/onboarding/screens/self_intro_screen.dart
//
// 사용 예시 (main.dart):
// import 'package:seolleyeon/features/onboarding/screens/self_intro_screen.dart';
// ...
// home: const SelfIntroScreen(),
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

// =============================================================================
// 색상 상수 (Cupertino 스타일)
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFEF3976);
  static const Color backgroundLight = Color(0xFFF8F6F6);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color textMain = Color(0xFF181113);
  static const Color textMuted = Color(0xFF89616F);
  static const Color borderLight = Color(0xFFE6DBDF);
}

// =============================================================================
// 메인 화면
// =============================================================================
class SelfIntroScreen extends StatefulWidget {
  const SelfIntroScreen({super.key});

  @override
  State<SelfIntroScreen> createState() => _SelfIntroScreenState();
}

class _SelfIntroScreenState extends State<SelfIntroScreen> {
  final TextEditingController _controller = TextEditingController();
  final int _maxLength = 300;
  int _currentLength = 0;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    setState(() {
      _currentLength = _controller.text.length;
    });
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    super.dispose();
  }

  void _insertSuggestion(String text) {
    final currentText = _controller.text;
    final newText = currentText.isEmpty ? text : '$currentText\n$text';
    if (newText.length <= _maxLength) {
      _controller.text = newText;
      _controller.selection = TextSelection.collapsed(offset: newText.length);
    }
    // 햅틱 피드백
    HapticFeedback.selectionClick();
  }

  void _onNextPressed() {
    if (_currentLength > 0) {
      // TODO: 다음 화면으로 이동
      HapticFeedback.mediumImpact();
    }
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            // 스크롤 가능한 메인 콘텐츠
            CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                // 네비게이션 바
                SliverToBoxAdapter(
                  child: _TopNavigationBar(
                    currentStep: 5,
                    totalSteps: 6,
                    onBackPressed: () => Navigator.of(context).pop(),
                  ),
                ),
                // 헤더 섹션
                const SliverToBoxAdapter(child: _HeaderSection()),
                // 텍스트 입력 영역
                SliverToBoxAdapter(
                  child: _TextInputArea(
                    controller: _controller,
                    maxLength: _maxLength,
                    currentLength: _currentLength,
                  ),
                ),
                // 제안 칩 섹션
                SliverToBoxAdapter(
                  child: _SuggestionSection(onSuggestionTap: _insertSuggestion),
                ),
                // 하단 버튼 공간 확보
                const SliverToBoxAdapter(child: SizedBox(height: 120)),
              ],
            ),
            // 하단 고정 CTA 버튼
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _BottomCTAButton(
                isEnabled: _currentLength > 0,
                onPressed: _onNextPressed,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 상단 네비게이션 바
// =============================================================================
class _TopNavigationBar extends StatelessWidget {
  final int currentStep;
  final int totalSteps;
  final VoidCallback onBackPressed;

  const _TopNavigationBar({
    required this.currentStep,
    required this.totalSteps,
    required this.onBackPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 뒤로가기 버튼
          CupertinoButton(
            padding: EdgeInsets.zero,
            minimumSize: const Size(44, 44),
            onPressed: onBackPressed,
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: CupertinoColors.white.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(22),
              ),
              child: const Icon(
                CupertinoIcons.back,
                color: _AppColors.textMain,
                size: 22,
              ),
            ),
          ),
          // 스텝 인디케이터
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: _AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '$currentStep/$totalSteps',
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: _AppColors.primary,
                letterSpacing: 0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 헤더 섹션 (제목 + 설명)
// =============================================================================
class _HeaderSection extends StatelessWidget {
  const _HeaderSection();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(24, 16, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '어떤 사람인지\n알려주세요',
            style: TextStyle(
              fontFamily: '.SF Pro Display',
              fontSize: 28,
              fontWeight: FontWeight.w700,
              height: 1.25,
              letterSpacing: -0.5,
              color: _AppColors.textMain,
            ),
          ),
          SizedBox(height: 12),
          Text(
            '상대방에게 매력을 어필할 수 있는 기회예요.\n솔직하고 담백하게 작성해보세요.',
            style: TextStyle(
              fontFamily: '.SF Pro Text',
              fontSize: 15,
              fontWeight: FontWeight.w400,
              height: 1.5,
              color: _AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 텍스트 입력 영역
// =============================================================================
class _TextInputArea extends StatelessWidget {
  final TextEditingController controller;
  final int maxLength;
  final int currentLength;

  const _TextInputArea({
    required this.controller,
    required this.maxLength,
    required this.currentLength,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Container(
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: _AppColors.borderLight, width: 1),
          boxShadow: [
            BoxShadow(
              color: CupertinoColors.black.withValues(alpha: 0.04),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            // 텍스트 입력 필드
            CupertinoTextField(
              controller: controller,
              maxLength: maxLength,
              maxLines: 6,
              minLines: 6,
              placeholder:
                  '커피 한 잔과 함께하는 조용한 대화를 좋아해요.\n주말에는 주로 한강에서 러닝을 즐겨요...',
              placeholderStyle: TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 16,
                fontWeight: FontWeight.w400,
                height: 1.5,
                color: _AppColors.textMuted.withValues(alpha: 0.6),
              ),
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 16,
                fontWeight: FontWeight.w400,
                height: 1.5,
                color: _AppColors.textMain,
              ),
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(),
              textAlignVertical: TextAlignVertical.top,
            ),
            // 글자 수 카운터
            Container(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              alignment: Alignment.centerRight,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: _AppColors.backgroundLight,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: RichText(
                  text: TextSpan(
                    style: const TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                    children: [
                      TextSpan(
                        text: '$currentLength',
                        style: const TextStyle(color: _AppColors.primary),
                      ),
                      TextSpan(
                        text: ' / $maxLength',
                        style: const TextStyle(color: _AppColors.textMuted),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 제안 칩 섹션
// =============================================================================
class _SuggestionSection extends StatelessWidget {
  final Function(String) onSuggestionTap;

  const _SuggestionSection({required this.onSuggestionTap});

  static const List<Map<String, String>> _suggestions = [
    {'emoji': '💊', 'text': '요즘 빠진 것'},
    {'emoji': '🧗', 'text': '주말 루틴'},
    {'emoji': '🍷', 'text': '좋아하는 데이트'},
    {'emoji': '✈️', 'text': '가고싶은 여행지'},
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 제안 헤더
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: _AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  CupertinoIcons.lightbulb,
                  color: _AppColors.primary,
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              const Text(
                '무엇을 쓸지 고민되시나요?',
                style: TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: _AppColors.textMain,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 제안 칩들
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: _suggestions.map((item) {
              return _SuggestionChip(
                emoji: item['emoji']!,
                text: item['text']!,
                onTap: () => onSuggestionTap(
                  '${item['emoji']} ${item['text']}에 대해 적어보세요...',
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 개별 제안 칩
// =============================================================================
class _SuggestionChip extends StatelessWidget {
  final String emoji;
  final String text;
  final VoidCallback onTap;

  const _SuggestionChip({
    required this.emoji,
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      minimumSize: Size.zero,
      onPressed: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: _AppColors.borderLight, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 6),
            Text(
              text,
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: _AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 하단 CTA 버튼
// =============================================================================
class _BottomCTAButton extends StatelessWidget {
  final bool isEnabled;
  final VoidCallback onPressed;

  const _BottomCTAButton({required this.isEnabled, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      // 그라데이션 배경으로 자연스러운 페이드 효과
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _AppColors.backgroundLight.withValues(alpha: 0.0),
            _AppColors.backgroundLight.withValues(alpha: 0.9),
            _AppColors.backgroundLight,
          ],
          stops: const [0.0, 0.3, 0.5],
        ),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: CupertinoButton(
            padding: EdgeInsets.zero,
            onPressed: isEnabled ? onPressed : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              width: double.infinity,
              height: 56,
              decoration: BoxDecoration(
                color: isEnabled
                    ? _AppColors.primary
                    : _AppColors.primary.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(16),
                boxShadow: isEnabled
                    ? [
                        BoxShadow(
                          color: _AppColors.primary.withValues(alpha: 0.35),
                          blurRadius: 20,
                          offset: const Offset(0, 8),
                        ),
                      ]
                    : [],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '다음',
                    style: TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: isEnabled
                          ? CupertinoColors.white
                          : CupertinoColors.white.withValues(alpha: 0.7),
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Icon(
                    CupertinoIcons.arrow_right,
                    color: isEnabled
                        ? CupertinoColors.white
                        : CupertinoColors.white.withValues(alpha: 0.7),
                    size: 18,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
