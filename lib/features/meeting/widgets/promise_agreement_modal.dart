// =============================================================================
// 약속 동의 모달 (바텀 시트)
// 경로: lib/features/meeting/widgets/promise_agreement_modal.dart
//
// 사용 예시:
// showCupertinoModalPopup(
//   context: context,
//   builder: (_) => const PromiseAgreementModal(),
// );
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF0426E);
  static const Color backgroundLight = Color(0xFFFDF9FA);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color textMain = Color(0xFF181113);
  static const Color textSecondary = Color(0xFF89616B);
  static const Color gray50 = Color(0xFFFAFAFA);
  static const Color gray200 = Color(0xFFE5E7EB);
}

// =============================================================================
// 규칙 아이템 모델
// =============================================================================
class _RuleItem {
  final IconData icon;
  final String title;
  final String description;

  const _RuleItem({
    required this.icon,
    required this.title,
    required this.description,
  });
}

// =============================================================================
// 메인 모달
// =============================================================================
class PromiseAgreementModal extends StatelessWidget {
  const PromiseAgreementModal({super.key});

  static const List<_RuleItem> _rules = [
    _RuleItem(
      icon: CupertinoIcons.camera,
      title: '본인 확인 및 얼굴 공개',
      description: '신뢰할 수 있는 분들과만 만날 수 있도록 프로필 사진을 꼼꼼히 확인해요.',
    ),
    _RuleItem(
      icon: CupertinoIcons.money_dollar_circle,
      title: '약속 머니 제도',
      description: '소중한 시간을 지키기 위해 소액의 보증금으로 노쇼(No-Show)를 방지해요.',
    ),
    _RuleItem(
      icon: CupertinoIcons.person_2,
      title: '대타 매칭 시스템',
      description: '갑작스러운 빈자리도 걱정 없어요. 검증된 대타 회원을 빠르게 연결해드려요.',
    ),
  ];

  void _onAgree(BuildContext context) {
    HapticFeedback.mediumImpact();
    Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.92,
      ),
      decoration: const BoxDecoration(
        color: _AppColors.surfaceLight,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(32),
          topRight: Radius.circular(32),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 핸들 바
          const _HandleBar(),
          // 콘텐츠
          Flexible(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
              child: Column(
                children: [
                  // 헤더 아이콘 & 타이틀
                  const _Header(),
                  const SizedBox(height: 32),
                  // 규칙 목록
                  ..._rules.map(
                    (rule) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _RuleCard(rule: rule),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
          // 하단 CTA
          Container(
            padding: EdgeInsets.fromLTRB(24, 12, 24, bottomPadding + 24),
            decoration: const BoxDecoration(
              color: _AppColors.surfaceLight,
              border: Border(top: BorderSide(color: _AppColors.gray50)),
            ),
            child: CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () => _onAgree(context),
              child: Container(
                width: double.infinity,
                height: 56,
                decoration: BoxDecoration(
                  color: _AppColors.primary,
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: [
                    BoxShadow(
                      color: _AppColors.primary.withValues(alpha: 0.3),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Center(
                  child: Text(
                    '동의하고 계속',
                    style: TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                      color: CupertinoColors.white,
                    ),
                  ),
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
// 핸들 바
// =============================================================================
class _HandleBar extends StatelessWidget {
  const _HandleBar();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Container(
        width: 48,
        height: 6,
        decoration: BoxDecoration(
          color: _AppColors.gray200,
          borderRadius: BorderRadius.circular(3),
        ),
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // 아이콘
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: _AppColors.primary.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            CupertinoIcons.shield_fill,
            color: _AppColors.primary,
            size: 32,
          ),
        ),
        const SizedBox(height: 20),
        // 타이틀
        const Text(
          '우리 함께 약속해요 🤍',
          style: TextStyle(
            fontFamily: '.SF Pro Display',
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: _AppColors.textMain,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 8),
        // 서브타이틀
        const Text(
          '즐겁고 안전한 만남을 위해\n서로를 배려하는 몇 가지 약속이 필요해요',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: '.SF Pro Text',
            fontSize: 14,
            height: 1.5,
            color: _AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 규칙 카드
// =============================================================================
class _RuleCard extends StatelessWidget {
  final _RuleItem rule;

  const _RuleCard({required this.rule});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _AppColors.backgroundLight,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 아이콘
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _AppColors.surfaceLight,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: CupertinoColors.black.withValues(alpha: 0.05),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Icon(rule.icon, color: _AppColors.primary, size: 20),
          ),
          const SizedBox(width: 16),
          // 텍스트
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 2),
                Text(
                  rule.title,
                  style: const TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: _AppColors.textMain,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  rule.description,
                  style: const TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 13,
                    height: 1.4,
                    color: _AppColors.textSecondary,
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
// 헬퍼 함수 - 모달 표시
// =============================================================================
Future<bool?> showPromiseAgreementModal(BuildContext context) {
  return showCupertinoModalPopup<bool>(
    context: context,
    builder: (_) => const PromiseAgreementModal(),
  );
}
