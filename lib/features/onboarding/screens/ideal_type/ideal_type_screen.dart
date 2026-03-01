// =============================================================================
// 이상형 정보 입력 화면 (이상형 설정 개요)
// 경로: lib/features/onboarding/screens/ideal_type/ideal_type_screen.dart
//
// 사용 예시 (main.dart):
// import 'package:seolleyeon/features/onboarding/screens/ideal_type/ideal_type_screen.dart';
// ...
// home: const IdealTypeScreen(),
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF43F7E);
  static const Color backgroundBase = Color(0xFFFDF7F9);
  static const Color surfaceWhite = Color(0xFFFFFFFF);
  static const Color textMain = Color(0xFF111827);
  static const Color textSub = Color(0xFF6B7280);
  static const Color gray50 = Color(0xFFF9FAFB);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray200 = Color(0xFFE5E7EB);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color dotInactive = Color(0xFFE5E7EB);
}

// =============================================================================
// 메인 화면
// =============================================================================
class IdealTypeScreen extends StatefulWidget {
  const IdealTypeScreen({super.key});

  @override
  State<IdealTypeScreen> createState() => _IdealTypeScreenState();
}

class _IdealTypeScreenState extends State<IdealTypeScreen> {
  // 선택된 값들 (실제로는 각 상세 화면에서 선택하고 setState로 업데이트)
  final String _height = '170';
  final String _age = '20 - 24';
  final String _mbti = 'E, N, F, J';
  final String _major = '예체능 계열';

  void _onHeightTap() {
    HapticFeedback.selectionClick();
    Navigator.of(context).pushNamed(RouteNames.onboardingIdealHeight);
  }

  void _onAgeTap() {
    HapticFeedback.selectionClick();
    Navigator.of(context).pushNamed(RouteNames.onboardingIdealAge);
  }

  void _onMbtiTap() {
    HapticFeedback.selectionClick();
    Navigator.of(context).pushNamed(RouteNames.onboardingIdealMbti);
  }

  void _onMajorTap() {
    HapticFeedback.selectionClick();
    Navigator.of(context).pushNamed(RouteNames.onboardingIdealDepartment);
  }

  void _onNextPressed() {
    HapticFeedback.mediumImpact();
    Navigator.of(context).pushNamed(RouteNames.onboardingIdealPersonality);
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundBase,
      child: Stack(
        children: [
          SafeArea(
            bottom: false,
            child: Column(
              children: [
                // 헤더
                _Header(
                  onBackPressed: () => Navigator.of(context).pop(),
                  currentStep: 1,
                  totalSteps: 3,
                ),
                // 스크롤 영역
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
                    child: _CardContainer(
                      child: Column(
                        children: [
                          const SizedBox(height: 24),
                          // 타이틀
                          const _TitleSection(),
                          const SizedBox(height: 32),
                          // 입력 필드들
                          _InputField(
                            label: '키',
                            value: _height,
                            suffix: 'cm',
                            icon: CupertinoIcons.resize_v,
                            onTap: _onHeightTap,
                          ),
                          const SizedBox(height: 20),
                          _InputField(
                            label: '나이',
                            value: _age,
                            suffix: '살',
                            icon: CupertinoIcons.gift,
                            onTap: _onAgeTap,
                          ),
                          const SizedBox(height: 20),
                          _InputField(
                            label: 'MBTI',
                            value: _mbti,
                            icon: CupertinoIcons.circle_grid_hex,
                            onTap: _onMbtiTap,
                          ),
                          const SizedBox(height: 20),
                          _InputField(
                            label: '학과',
                            labelSuffix: '(중복 선택 가능)',
                            value: _major,
                            icon: CupertinoIcons.book,
                            onTap: _onMajorTap,
                          ),
                          const SizedBox(height: 32),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // 하단 CTA 버튼
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _BottomCTA(onPressed: _onNextPressed),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final VoidCallback onBackPressed;
  final int currentStep;
  final int totalSteps;

  const _Header({
    required this.onBackPressed,
    required this.currentStep,
    required this.totalSteps,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Row(
        children: [
          CupertinoButton(
            padding: EdgeInsets.zero,
            minimumSize: const Size(44, 44),
            onPressed: onBackPressed,
            child: const Icon(
              CupertinoIcons.back,
              color: _AppColors.textMain,
              size: 24,
            ),
          ),
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(totalSteps, (index) {
                final isActive = index == currentStep - 1;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  width: isActive ? 24 : 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: isActive
                        ? _AppColors.primary
                        : _AppColors.dotInactive,
                    borderRadius: BorderRadius.circular(5),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(width: 44),
        ],
      ),
    );
  }
}

// =============================================================================
// 카드 컨테이너
// =============================================================================
class _CardContainer extends StatelessWidget {
  final Widget child;

  const _CardContainer({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: _AppColors.surfaceWhite,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: CupertinoColors.black.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: child,
      ),
    );
  }
}

// =============================================================================
// 타이틀 섹션
// =============================================================================
class _TitleSection extends StatelessWidget {
  const _TitleSection();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Text(
          '이상형 정보',
          style: TextStyle(
            fontFamily: '.SF Pro Display',
            fontSize: 24,
            fontWeight: FontWeight.w800,
            color: _AppColors.textMain,
          ),
        ),
        SizedBox(height: 8),
        Text(
          '매칭을 위해 이상형 정보를 입력해주세요.',
          style: TextStyle(
            fontFamily: '.SF Pro Text',
            fontSize: 14,
            fontWeight: FontWeight.w400,
            color: _AppColors.textSub,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 입력 필드
// =============================================================================
class _InputField extends StatelessWidget {
  final String label;
  final String? labelSuffix;
  final String value;
  final String? suffix;
  final IconData icon;
  final VoidCallback onTap;

  const _InputField({
    required this.label,
    this.labelSuffix,
    required this.value,
    this.suffix,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 라벨
        Row(
          children: [
            Text(
              label,
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: _AppColors.textMain,
              ),
            ),
            if (labelSuffix != null) ...[
              const SizedBox(width: 4),
              Text(
                labelSuffix!,
                style: const TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                  color: _AppColors.gray400,
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 12),
        // 입력 박스
        CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: onTap,
          child: Container(
            height: 52,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: _AppColors.gray50,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _AppColors.gray100),
            ),
            child: Row(
              children: [
                Icon(icon, size: 18, color: _AppColors.gray400),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    value,
                    style: const TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _AppColors.textSub,
                    ),
                  ),
                ),
                if (suffix != null) ...[
                  Text(
                    suffix!,
                    style: const TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _AppColors.textSub,
                    ),
                  ),
                ],
                const SizedBox(width: 8),
                const Icon(
                  CupertinoIcons.chevron_right,
                  size: 16,
                  color: _AppColors.gray400,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 하단 CTA 버튼
// =============================================================================
class _BottomCTA extends StatelessWidget {
  final VoidCallback onPressed;

  const _BottomCTA({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding + 16),
      decoration: BoxDecoration(
        color: _AppColors.backgroundBase.withValues(alpha: 0.9),
      ),
      child: CupertinoButton(
        padding: EdgeInsets.zero,
        onPressed: onPressed,
        child: Container(
          width: double.infinity,
          height: 56,
          decoration: BoxDecoration(
            color: _AppColors.primary,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: _AppColors.primary.withValues(alpha: 0.4),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '다음',
                style: TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: CupertinoColors.white,
                ),
              ),
              SizedBox(width: 6),
              Icon(
                CupertinoIcons.arrow_right,
                size: 18,
                color: CupertinoColors.white,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
