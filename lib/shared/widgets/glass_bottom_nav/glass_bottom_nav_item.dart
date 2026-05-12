// =============================================================================
// Glass Bottom Navigation Bar — Item Model
// =============================================================================

import 'package:flutter/cupertino.dart';

/// A single tab descriptor for [GlassBottomNavBar].
///
/// Supports icon-only, icon + label, badge dot, badge count, and an optional
/// avatar image (e.g. for profile tabs).
class GlassNavItem {
  /// Icon shown when the item is **not** selected.
  final IconData icon;

  /// Icon shown when the item **is** selected.
  /// Falls back to [icon] if null.
  final IconData? activeIcon;

  /// Optional text label beneath the icon.
  final String? label;

  /// If > 0, a small count badge is rendered at the icon's top-right.
  final int badgeCount;

  /// If `true`, a plain colored dot is rendered at the icon's top-right.
  /// Ignored when [badgeCount] > 0.
  final bool showDot;

  /// If provided, renders a circular avatar instead of the icon.
  /// Useful for profile tabs.
  final ImageProvider? avatarImage;

  /// Semantics label for accessibility.
  final String? semanticsLabel;

  const GlassNavItem({
    required this.icon,
    this.activeIcon,
    this.label,
    this.badgeCount = 0,
    this.showDot = false,
    this.avatarImage,
    this.semanticsLabel,
  });

  GlassNavItem copyWith({
    IconData? icon,
    IconData? activeIcon,
    String? label,
    int? badgeCount,
    bool? showDot,
    ImageProvider? avatarImage,
    String? semanticsLabel,
  }) {
    return GlassNavItem(
      icon: icon ?? this.icon,
      activeIcon: activeIcon ?? this.activeIcon,
      label: label ?? this.label,
      badgeCount: badgeCount ?? this.badgeCount,
      showDot: showDot ?? this.showDot,
      avatarImage: avatarImage ?? this.avatarImage,
      semanticsLabel: semanticsLabel ?? this.semanticsLabel,
    );
  }
}
