// =============================================================================
// 키 선택 화면 (온보딩)
// 경로: lib/features/onboarding/screens/height_selection_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const HeightSelectionScreen()),
// );
// =============================================================================

import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF8E9E);
  static const Color backgroundLight = Color(0xFFFAFAFB);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color textMainLight = Color(0xFF191F28);
  static const Color textSecondaryLight = Color(0xFF8B95A1);
  static const Color gray50 = Color(0xFFF9FAFB);
}

// =============================================================================
// 메인 화면
// =============================================================================
class HeightSelectionScreen extends StatefulWidget {
  final int initialHeight;
  final int minHeight;
  final int maxHeight;
  final VoidCallback? onBack;
  final Function(int height)? onComplete;

  const HeightSelectionScreen({
    super.key,
    this.initialHeight = 175,
    this.minHeight = 140,
    this.maxHeight = 200,
    this.onBack,
    this.onComplete,
  });

  @override
  State<HeightSelectionScreen> createState() => _HeightSelectionScreenState();
}

class _HeightSelectionScreenState extends State<HeightSelectionScreen> {
  late FixedExtentScrollController _scrollController;
  late int _selectedHeight;

  @override
  void initState() {
    super.initState();
    _selectedHeight = widget.initialHeight;
    _scrollController = FixedExtentScrollController(
      initialItem: widget.initialHeight - widget.minHeight,
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: Stack(
        children: [
          // 배경 그라데이션
          _BackgroundGradients(),
          // 메인 콘텐츠
          SafeArea(
            child: Column(
              children: [
                // 상단 로고
                const SizedBox(height: 48),
                Center(
                  child: Opacity(
                    opacity: 0.5,
                    child: const Text(
                      '설레연',
                      style: TextStyle(
                        fontFamily: '.SF Pro Display',
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.3,
                        color: _AppColors.textSecondaryLight,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // 메인 카드
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: _SelectionCard(
                      selectedHeight: _selectedHeight,
                      minHeight: widget.minHeight,
                      maxHeight: widget.maxHeight,
                      scrollController: _scrollController,
                      onHeightChanged: (height) {
                        setState(() => _selectedHeight = height);
                      },
                      onComplete: () {
                        HapticFeedback.mediumImpact();
                        if (widget.onComplete != null) {
                          widget.onComplete!.call(_selectedHeight);
                        } else {
                          Navigator.of(context).pushNamed(RouteNames.onboardingBasicInfo);
                        }
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
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
          right: -100,
          child: Container(
            width: 600,
            height: 600,
            decoration: BoxDecoration(
              color: _AppColors.primary.withValues(alpha: 0.05),
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
          left: -100,
          child: Container(
            width: 500,
            height: 500,
            decoration: BoxDecoration(
              color: const Color(0xFFDBEAFE).withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
              child: const SizedBox(),
            ),
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 선택 카드
// =============================================================================
class _SelectionCard extends StatelessWidget {
  final int selectedHeight;
  final int minHeight;
  final int maxHeight;
  final FixedExtentScrollController scrollController;
  final Function(int height) onHeightChanged;
  final VoidCallback onComplete;

  const _SelectionCard({
    required this.selectedHeight,
    required this.minHeight,
    required this.maxHeight,
    required this.scrollController,
    required this.onHeightChanged,
    required this.onComplete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: CupertinoColors.black.withValues(alpha: 0.05),
            blurRadius: 60,
            offset: const Offset(0, 20),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            const SizedBox(height: 16),
            // 타이틀
            const Text(
              '키를 알려주세요',
              style: TextStyle(
                fontFamily: '.SF Pro Display',
                fontSize: 26,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
                color: _AppColors.textMainLight,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '솔직하게 입력해 주세요',
              style: TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: _AppColors.textSecondaryLight,
              ),
            ),
            const SizedBox(height: 40),
            // 피커
            Expanded(
              child: _HeightPicker(
                minHeight: minHeight,
                maxHeight: maxHeight,
                scrollController: scrollController,
                onHeightChanged: onHeightChanged,
              ),
            ),
            const SizedBox(height: 16),
            // 선택된 값 표시
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                color: _AppColors.gray50,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                '${selectedHeight}cm',
                style: const TextStyle(
                  fontFamily: '.SF Pro Display',
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: _AppColors.textMainLight,
                ),
              ),
            ),
            const SizedBox(height: 48),
            // 완료 버튼
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: onComplete,
              child: Container(
                width: double.infinity,
                height: 56,
                decoration: BoxDecoration(
                  color: _AppColors.primary,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: _AppColors.primary.withValues(alpha: 0.3),
                      blurRadius: 24,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Center(
                  child: Text(
                    '완료',
                    style: TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 17,
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
    );
  }
}

// =============================================================================
// 키 피커
// =============================================================================
class _HeightPicker extends StatelessWidget {
  final int minHeight;
  final int maxHeight;
  final FixedExtentScrollController scrollController;
  final Function(int height) onHeightChanged;

  const _HeightPicker({
    required this.minHeight,
    required this.maxHeight,
    required this.scrollController,
    required this.onHeightChanged,
  });

  @override
  Widget build(BuildContext context) {
    final itemCount = maxHeight - minHeight + 1;

    return Stack(
      children: [
        // 선택 영역 하이라이트
        Center(
          child: Container(
            width: MediaQuery.of(context).size.width * 0.6,
            height: 48,
            decoration: BoxDecoration(
              color: _AppColors.gray50,
              borderRadius: BorderRadius.circular(16),
            ),
          ),
        ),
        // 피커
        ShaderMask(
          shaderCallback: (Rect bounds) {
            return const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0x00FFFFFF),
                Color(0xFFFFFFFF),
                Color(0xFFFFFFFF),
                Color(0x00FFFFFF),
              ],
              stops: [0.0, 0.3, 0.7, 1.0],
            ).createShader(bounds);
          },
          blendMode: BlendMode.dstIn,
          child: CupertinoPicker(
            scrollController: scrollController,
            itemExtent: 48,
            diameterRatio: 1.5,
            squeeze: 1.0,
            selectionOverlay: const SizedBox(),
            onSelectedItemChanged: (index) {
              HapticFeedback.selectionClick();
              onHeightChanged(minHeight + index);
            },
            children: List.generate(itemCount, (index) {
              final height = minHeight + index;
              return Center(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      '$height',
                      style: const TextStyle(
                        fontFamily: '.SF Pro Display',
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.5,
                        color: _AppColors.textMainLight,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      'cm',
                      style: TextStyle(
                        fontFamily: '.SF Pro Text',
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                        color: _AppColors.textSecondaryLight,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ],
    );
  }
}
