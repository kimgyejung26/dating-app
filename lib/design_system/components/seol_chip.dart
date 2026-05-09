import 'package:flutter/material.dart';
import '../seol_colors.dart';

/// 설레연 태그 칩 타입
enum SeolChipType { emotion, filter, selection }

/// 설레연 태그 칩 컴포넌트
class SeolChip extends StatelessWidget {
  final String label;
  final SeolChipType type;
  final bool isSelected;
  final VoidCallback? onTap;
  final IconData? icon;
  final Color? customColor;

  const SeolChip({
    super.key,
    required this.label,
    this.type = SeolChipType.emotion,
    this.isSelected = false,
    this.onTap,
    this.icon,
    this.customColor,
  });

  Color get _backgroundColor {
    if (isSelected) {
      return customColor ?? SeolColors.primary;
    }
    switch (type) {
      case SeolChipType.emotion:
        return _getEmotionColor(label);
      case SeolChipType.filter:
        return SeolColors.backgroundGrey;
      case SeolChipType.selection:
        return SeolColors.backgroundWhite;
    }
  }

  Color get _textColor {
    if (isSelected) {
      return SeolColors.textWhite;
    }
    switch (type) {
      case SeolChipType.emotion:
        return SeolColors.primary;
      case SeolChipType.filter:
        return SeolColors.textSecondary;
      case SeolChipType.selection:
        return SeolColors.textPrimary;
    }
  }

  Border? get _border {
    if (type == SeolChipType.selection && !isSelected) {
      return Border.all(color: SeolColors.borderMedium);
    }
    return null;
  }

  Color _getEmotionColor(String emotion) {
    switch (emotion) {
      case '두근':
      case '썸사랑':
        return SeolColors.tagExcitement;
      case '첫미팅':
      case '첫만남':
        return SeolColors.tagFirstMeet;
      case '고민':
        return SeolColors.tagWorry;
      case '성공후기':
        return SeolColors.tagSuccess;
      default:
        return customColor ?? SeolColors.primarySoft;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: _backgroundColor,
          borderRadius: BorderRadius.circular(20),
          border: _border,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 16, color: _textColor),
              const SizedBox(width: 6),
            ],
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: _textColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 필터 탭 바 (대나무숲용)
class SeolFilterTabs extends StatelessWidget {
  final List<String> tabs;
  final int selectedIndex;
  final ValueChanged<int> onTabSelected;

  const SeolFilterTabs({
    super.key,
    required this.tabs,
    required this.selectedIndex,
    required this.onTabSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: List.generate(tabs.length, (index) {
          final isSelected = index == selectedIndex;
          return Padding(
            padding: EdgeInsets.only(right: index < tabs.length - 1 ? 8 : 0),
            child: SeolChip(
              label: tabs[index],
              type: SeolChipType.filter,
              isSelected: isSelected,
              onTap: () => onTabSelected(index),
            ),
          );
        }),
      ),
    );
  }
}
