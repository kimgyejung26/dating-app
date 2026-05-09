import 'package:flutter/material.dart';
import '../seol_colors.dart';
import '../seol_typography.dart';

/// 설레연 바텀시트 표시
Future<T?> showSeolBottomSheet<T>({
  required BuildContext context,
  required Widget child,
  String? title,
  bool isDismissible = true,
  bool enableDrag = true,
  double? height,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    isDismissible: isDismissible,
    enableDrag: enableDrag,
    backgroundColor: Colors.transparent,
    builder: (context) =>
        SeolBottomSheet(title: title, height: height, child: child),
  );
}

/// 설레연 바텀시트 컨테이너
class SeolBottomSheet extends StatelessWidget {
  final Widget child;
  final String? title;
  final double? height;

  const SeolBottomSheet({
    super.key,
    required this.child,
    this.title,
    this.height,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: const BoxDecoration(
        color: SeolColors.backgroundWhite,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: SeolColors.borderMedium,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          // Title
          if (title != null)
            Padding(
              padding: const EdgeInsets.only(top: 20, bottom: 8),
              child: Text(title!, style: SeolTypography.h4),
            ),
          // Content
          Flexible(
            child: Padding(padding: const EdgeInsets.all(20), child: child),
          ),
        ],
      ),
    );
  }
}

/// 신고/차단 메뉴 바텀시트
Future<void> showSeolActionSheet({
  required BuildContext context,
  required List<SeolActionItem> actions,
  String? title,
}) {
  return showSeolBottomSheet(
    context: context,
    title: title,
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: actions
          .map(
            (action) => _ActionRow(
              icon: action.icon,
              label: action.label,
              isDestructive: action.isDestructive,
              onTap: () {
                Navigator.pop(context);
                action.onTap?.call();
              },
            ),
          )
          .toList(),
    ),
  );
}

class SeolActionItem {
  final IconData icon;
  final String label;
  final bool isDestructive;
  final VoidCallback? onTap;

  const SeolActionItem({
    required this.icon,
    required this.label,
    this.isDestructive = false,
    this.onTap,
  });
}

class _ActionRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isDestructive;
  final VoidCallback? onTap;

  const _ActionRow({
    required this.icon,
    required this.label,
    this.isDestructive = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isDestructive ? SeolColors.error : SeolColors.textPrimary;

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(width: 14),
            Text(
              label,
              style: SeolTypography.labelLarge.copyWith(color: color),
            ),
          ],
        ),
      ),
    );
  }
}

/// 확인 다이얼로그
Future<bool?> showSeolConfirmDialog({
  required BuildContext context,
  required String title,
  required String message,
  String confirmText = '확인',
  String cancelText = '취소',
  bool isDestructive = false,
}) {
  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Text(title, style: SeolTypography.h4),
      content: Text(message, style: SeolTypography.bodyMedium),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text(
            cancelText,
            style: SeolTypography.labelMedium.copyWith(
              color: SeolColors.textSecondary,
            ),
          ),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text(
            confirmText,
            style: SeolTypography.labelMedium.copyWith(
              color: isDestructive ? SeolColors.error : SeolColors.primary,
            ),
          ),
        ),
      ],
    ),
  );
}
