import 'package:flutter/material.dart';
import '../seol_colors.dart';

/// 설레연 공통 스캐폴드 (그라데이션 배경)
class SeolScaffold extends StatelessWidget {
  final PreferredSizeWidget? appBar;
  final Widget body;
  final Widget? bottomNavigationBar;
  final Widget? floatingActionButton;
  final bool useGradient;
  final Color? backgroundColor;
  final bool extendBodyBehindAppBar;
  final bool resizeToAvoidBottomInset;

  const SeolScaffold({
    super.key,
    this.appBar,
    required this.body,
    this.bottomNavigationBar,
    this.floatingActionButton,
    this.useGradient = true,
    this.backgroundColor,
    this.extendBodyBehindAppBar = false,
    this.resizeToAvoidBottomInset = true,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      resizeToAvoidBottomInset: resizeToAvoidBottomInset,
      appBar: appBar,
      body: useGradient
          ? Container(
              decoration: const BoxDecoration(
                gradient: SeolColors.backgroundGradient,
              ),
              child: body,
            )
          : Container(
              color: backgroundColor ?? SeolColors.backgroundLight,
              child: body,
            ),
      bottomNavigationBar: bottomNavigationBar,
      floatingActionButton: floatingActionButton,
    );
  }
}

/// 설레연 세이프 에어리어 패딩 래퍼
class SeolSafeArea extends StatelessWidget {
  final Widget child;
  final bool top;
  final bool bottom;
  final EdgeInsetsGeometry? padding;

  const SeolSafeArea({
    super.key,
    required this.child,
    this.top = true,
    this.bottom = true,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: top,
      bottom: bottom,
      child: Padding(
        padding:
            padding ?? const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: child,
      ),
    );
  }
}
