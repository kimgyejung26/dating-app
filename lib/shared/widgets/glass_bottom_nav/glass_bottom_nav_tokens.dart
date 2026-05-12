// =============================================================================
// Glass Bottom Navigation Bar — Design Tokens
// =============================================================================
//
// Central source of truth for every visual token used by GlassBottomNavBar.
// Three built-in presets map to the three reference aesthetics:
//
//   softLight   → bright frosted-white glass (배민-style light)
//   darkLens    → deep charcoal glass with lens-capsule (dark premium)
//   darkMinimal → Instagram-like minimal dark translucent bar
//
// All values are intentionally kept as plain Dart const / final so they can
// be tree-shaken and are easy to override per-instance.
// =============================================================================

import 'package:flutter/cupertino.dart';

// ─── Variant enum ────────────────────────────────────────────────────────────

/// Visual preset for [GlassBottomNavBar].
enum GlassNavVariant {
  /// Bright frosted-white glass on light backgrounds.
  softLight,

  /// Deep charcoal glass with protruding lens capsule on dark backgrounds.
  darkLens,

  /// Instagram-like minimal dark translucent bar.
  darkMinimal,
}

// ─── Style data class ────────────────────────────────────────────────────────

/// Immutable bag of visual tokens consumed by the nav bar renderer.
class GlassNavStyle {
  // ── Bar geometry ──────────────────────────────────────────────────────────
  /// Fractional width relative to screen width (0..1).
  final double barWidthFraction;

  /// Total bar height (dp).
  final double barHeight;

  /// Border radius of the bar pill.
  final double barRadius;

  /// Bottom margin from safe-area bottom.
  final double bottomMargin;

  // ── Bar surface ───────────────────────────────────────────────────────────
  /// Primary fill color of the bar (translucent).
  final Color barColor;

  /// Optional secondary gradient stop (top → bottom).
  final Color? barGradientEnd;

  /// 1 px border color (highlight rim).
  final Color borderColor;

  /// Outer shadow.
  final List<BoxShadow> barShadow;

  /// Backdrop blur sigma.
  final double blurSigma;

  // ── Inner highlight ───────────────────────────────────────────────────────
  /// Thin top highlight gradient start (opaque white → transparent).
  final Color innerHighlightColor;
  final double innerHighlightHeight;

  // ── Active capsule ────────────────────────────────────────────────────────
  /// Capsule height. Width is computed per-item slot.
  final double capsuleHeight;

  /// Capsule border radius.
  final double capsuleRadius;

  /// Vertical offset — negative means capsule protrudes upward.
  final double capsuleVerticalOffset;

  /// Capsule fill.
  final Color capsuleColor;

  /// Optional capsule gradient end.
  final Color? capsuleGradientEnd;

  /// Capsule border.
  final Color capsuleBorder;

  /// Capsule shadow.
  final List<BoxShadow> capsuleShadow;

  /// Capsule blur sigma (0 = no blur on capsule itself).
  final double capsuleBlurSigma;

  /// Whether to draw an extremely subtle chromatic edge fringe on the active
  /// capsule. Only meaningful for dark variants.
  final bool capsuleChromaticFringe;

  // ── Icon / label ──────────────────────────────────────────────────────────
  final double iconSizeInactive;
  final double iconSizeActive;
  final Color iconColorInactive;
  final Color iconColorActive;
  final double labelSize;
  final FontWeight labelWeightInactive;
  final FontWeight labelWeightActive;
  final Color labelColorInactive;
  final Color labelColorActive;
  final double iconLabelGap;

  // ── Badge ─────────────────────────────────────────────────────────────────
  final Color badgeDotColor;
  final double badgeDotSize;
  final Color badgeCountBg;
  final Color badgeCountFg;
  final double badgeCountSize;

  // ── Animation ─────────────────────────────────────────────────────────────
  final Duration animDuration;
  final Curve animCurve;

  const GlassNavStyle({
    this.barWidthFraction = 0.88,
    this.barHeight = 72,
    this.barRadius = 36,
    this.bottomMargin = 14,
    required this.barColor,
    this.barGradientEnd,
    required this.borderColor,
    this.barShadow = const [],
    this.blurSigma = 18,
    this.innerHighlightColor = const Color(0x18FFFFFF),
    this.innerHighlightHeight = 0.45,
    this.capsuleHeight = 62,
    this.capsuleRadius = 30,
    this.capsuleVerticalOffset = 0,
    required this.capsuleColor,
    this.capsuleGradientEnd,
    required this.capsuleBorder,
    this.capsuleShadow = const [],
    this.capsuleBlurSigma = 0,
    this.capsuleChromaticFringe = false,
    this.iconSizeInactive = 26,
    this.iconSizeActive = 28,
    required this.iconColorInactive,
    required this.iconColorActive,
    this.labelSize = 11,
    this.labelWeightInactive = FontWeight.w500,
    this.labelWeightActive = FontWeight.w700,
    required this.labelColorInactive,
    required this.labelColorActive,
    this.iconLabelGap = 3,
    this.badgeDotColor = const Color(0xFFFF3B30),
    this.badgeDotSize = 8,
    this.badgeCountBg = const Color(0xFFFF3B30),
    this.badgeCountFg = const Color(0xFFFFFFFF),
    this.badgeCountSize = 16,
    this.animDuration = const Duration(milliseconds: 200),
    this.animCurve = Curves.fastOutSlowIn,
  });

  // ── Built-in presets ──────────────────────────────────────────────────────

  /// **softLight** — frosted-white glass on light backgrounds.
  static const softLight = GlassNavStyle(
    barWidthFraction: 0.90,
    barHeight: 74,
    barRadius: 36,
    bottomMargin: 14,
    barColor: Color(0xE8FFFFFF),
    barGradientEnd: Color(0xD8F0EEFA),
    borderColor: Color(0x55FFFFFF),
    barShadow: [
      BoxShadow(
        color: Color(0x1A6B5880),
        blurRadius: 28,
        offset: Offset(0, 12),
        spreadRadius: 0,
      ),
      BoxShadow(
        color: Color(0x0A000000),
        blurRadius: 8,
        offset: Offset(0, 2),
        spreadRadius: 0,
      ),
    ],
    blurSigma: 20,
    innerHighlightColor: Color(0x22FFFFFF),
    innerHighlightHeight: 0.42,
    capsuleHeight: 62,
    capsuleRadius: 28,
    capsuleVerticalOffset: -2,
    capsuleColor: Color(0xF0FFFFFF),
    capsuleGradientEnd: Color(0xE0EBE8F8),
    capsuleBorder: Color(0x40FFFFFF),
    capsuleShadow: [
      BoxShadow(
        color: Color(0x18A090C0),
        blurRadius: 16,
        offset: Offset(0, 4),
        spreadRadius: 0,
      ),
    ],
    capsuleBlurSigma: 6,
    capsuleChromaticFringe: false,
    iconSizeInactive: 26,
    iconSizeActive: 28,
    iconColorInactive: Color(0xFF8E8E93),
    iconColorActive: Color(0xFF1C1440),
    labelSize: 11,
    labelWeightInactive: FontWeight.w500,
    labelWeightActive: FontWeight.w700,
    labelColorInactive: Color(0xFF8E8E93),
    labelColorActive: Color(0xFF1C1440),
    iconLabelGap: 3,
    badgeDotColor: Color(0xFFFF3B30),
    badgeDotSize: 8,
    badgeCountBg: Color(0xFFFED941),
    badgeCountFg: Color(0xFF1C1440),
    badgeCountSize: 18,
    animDuration: Duration(milliseconds: 200),
    animCurve: Curves.fastOutSlowIn,
  );

  /// **darkLens** — deep charcoal glass with lens-like active capsule.
  static const darkLens = GlassNavStyle(
    barWidthFraction: 0.90,
    barHeight: 76,
    barRadius: 38,
    bottomMargin: 14,
    barColor: Color(0xE01A1A1E),
    barGradientEnd: Color(0xD0222228),
    borderColor: Color(0x25FFFFFF),
    barShadow: [
      BoxShadow(
        color: Color(0x50000000),
        blurRadius: 32,
        offset: Offset(0, 14),
        spreadRadius: 0,
      ),
    ],
    blurSigma: 22,
    innerHighlightColor: Color(0x0CFFFFFF),
    innerHighlightHeight: 0.38,
    capsuleHeight: 66,
    capsuleRadius: 32,
    capsuleVerticalOffset: -4,
    capsuleColor: Color(0xC03A3A42),
    capsuleGradientEnd: Color(0xA02E2E38),
    capsuleBorder: Color(0x28FFFFFF),
    capsuleShadow: [
      BoxShadow(
        color: Color(0x30000000),
        blurRadius: 20,
        offset: Offset(0, 6),
        spreadRadius: 2,
      ),
    ],
    capsuleBlurSigma: 10,
    capsuleChromaticFringe: true,
    iconSizeInactive: 26,
    iconSizeActive: 28,
    iconColorInactive: Color(0xFF78788A),
    iconColorActive: Color(0xFFF2F2F7),
    labelSize: 11,
    labelWeightInactive: FontWeight.w500,
    labelWeightActive: FontWeight.w700,
    labelColorInactive: Color(0xFF78788A),
    labelColorActive: Color(0xFFF2F2F7),
    iconLabelGap: 3,
    badgeDotColor: Color(0xFFFF3B30),
    badgeDotSize: 8,
    badgeCountBg: Color(0xFFFED941),
    badgeCountFg: Color(0xFF1C1440),
    badgeCountSize: 18,
    animDuration: Duration(milliseconds: 200),
    animCurve: Curves.fastOutSlowIn,
  );

  /// **darkMinimal** — Instagram-like minimal dark translucent bar.
  static const darkMinimal = GlassNavStyle(
    barWidthFraction: 0.88,
    barHeight: 70,
    barRadius: 34,
    bottomMargin: 12,
    barColor: Color(0xE0161618),
    barGradientEnd: Color(0xD01C1C20),
    borderColor: Color(0x1AFFFFFF),
    barShadow: [
      BoxShadow(
        color: Color(0x44000000),
        blurRadius: 24,
        offset: Offset(0, 10),
        spreadRadius: 0,
      ),
    ],
    blurSigma: 16,
    innerHighlightColor: Color(0x08FFFFFF),
    innerHighlightHeight: 0.35,
    capsuleHeight: 54,
    capsuleRadius: 24,
    capsuleVerticalOffset: 0,
    capsuleColor: Color(0x90404048),
    capsuleBorder: Color(0x1EFFFFFF),
    capsuleShadow: [],
    capsuleBlurSigma: 0,
    capsuleChromaticFringe: false,
    iconSizeInactive: 26,
    iconSizeActive: 27,
    iconColorInactive: Color(0xFF6C6C72),
    iconColorActive: Color(0xFFEAEAEF),
    labelSize: 10,
    labelWeightInactive: FontWeight.w500,
    labelWeightActive: FontWeight.w600,
    labelColorInactive: Color(0xFF6C6C72),
    labelColorActive: Color(0xFFEAEAEF),
    iconLabelGap: 2,
    badgeDotColor: Color(0xFFFF3B30),
    badgeDotSize: 7,
    badgeCountBg: Color(0xFFFF3B30),
    badgeCountFg: Color(0xFFFFFFFF),
    badgeCountSize: 16,
    animDuration: Duration(milliseconds: 180),
    animCurve: Curves.easeOutCubic,
  );

  /// Resolve a [GlassNavVariant] to its built-in preset.
  static GlassNavStyle fromVariant(GlassNavVariant v) {
    switch (v) {
      case GlassNavVariant.softLight:
        return softLight;
      case GlassNavVariant.darkLens:
        return darkLens;
      case GlassNavVariant.darkMinimal:
        return darkMinimal;
    }
  }
}
