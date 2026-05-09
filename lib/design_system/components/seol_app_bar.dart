import 'package:flutter/material.dart';
import '../seol_colors.dart';
import '../seol_typography.dart';

/// 설레연 커스텀 앱바
class SeolAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? title;
  final Widget? titleWidget;
  final bool showBackButton;
  final VoidCallback? onBackPressed;
  final List<Widget>? actions;
  final Color? backgroundColor;
  final bool centerTitle;
  final double elevation;

  const SeolAppBar({
    super.key,
    this.title,
    this.titleWidget,
    this.showBackButton = true,
    this.onBackPressed,
    this.actions,
    this.backgroundColor,
    this.centerTitle = true,
    this.elevation = 0,
  });

  @override
  Size get preferredSize => const Size.fromHeight(56);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: backgroundColor ?? SeolColors.backgroundWhite,
      elevation: elevation,
      centerTitle: centerTitle,
      automaticallyImplyLeading: false,
      leading: showBackButton
          ? IconButton(
              onPressed: onBackPressed ?? () => Navigator.of(context).pop(),
              icon: const Icon(
                Icons.arrow_back_ios,
                color: SeolColors.textPrimary,
                size: 20,
              ),
            )
          : null,
      title:
          titleWidget ??
          (title != null
              ? Text(
                  title!,
                  style: SeolTypography.h4.copyWith(
                    color: SeolColors.textPrimary,
                  ),
                )
              : null),
      actions: actions,
    );
  }
}

/// 설레연 메인 탭 앱바 (로고 + 알림)
class SeolMainAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final VoidCallback? onNotificationTap;
  final List<Widget>? actions;

  const SeolMainAppBar({
    super.key,
    required this.title,
    this.onNotificationTap,
    this.actions,
  });

  @override
  Size get preferredSize => const Size.fromHeight(56);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: SeolColors.backgroundWhite,
      elevation: 0,
      automaticallyImplyLeading: false,
      title: Row(
        children: [
          Icon(Icons.favorite, color: SeolColors.primary, size: 24),
          const SizedBox(width: 8),
          Text(
            title,
            style: SeolTypography.h3.copyWith(color: SeolColors.textPrimary),
          ),
        ],
      ),
      actions:
          actions ??
          [
            IconButton(
              onPressed: onNotificationTap,
              icon: const Icon(
                Icons.notifications_outlined,
                color: SeolColors.textPrimary,
              ),
            ),
          ],
    );
  }
}
