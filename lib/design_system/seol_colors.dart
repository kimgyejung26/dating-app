import 'package:flutter/material.dart';

/// 설레연 앱 디자인 시스템 - 색상 팔레트
/// 프리미엄 / 차분 / 신뢰 / 사적인 공간 톤
class SeolColors {
  SeolColors._();

  // ─────────────────────────────────────────────
  // Primary Colors (Coral Pink)
  // ─────────────────────────────────────────────
  static const Color primary = Color(0xFFFF6B7A);
  static const Color primaryLight = Color(0xFFFF8A9B);
  static const Color primaryDark = Color(0xFFE85A69);
  static const Color primarySoft = Color(0xFFFFE4E7);

  // ─────────────────────────────────────────────
  // Secondary Colors (Soft Purple/Lavender)
  // ─────────────────────────────────────────────
  static const Color secondary = Color(0xFFB794F6);
  static const Color secondaryLight = Color(0xFFE9DFFF);
  static const Color secondaryDark = Color(0xFF9575CD);

  // ─────────────────────────────────────────────
  // Background Colors
  // ─────────────────────────────────────────────
  static const Color backgroundWhite = Color(0xFFFFFFFF);
  static const Color backgroundLight = Color(0xFFFAF9FC);
  static const Color backgroundSoft = Color(0xFFFFF5F6);
  static const Color backgroundCard = Color(0xFFFFFFFF);
  static const Color backgroundGrey = Color(0xFFF5F5F5);

  // ─────────────────────────────────────────────
  // Text Colors
  // ─────────────────────────────────────────────
  static const Color textPrimary = Color(0xFF1A1A1A);
  static const Color textSecondary = Color(0xFF6B6B6B);
  static const Color textTertiary = Color(0xFF9E9E9E);
  static const Color textHint = Color(0xFFBDBDBD);
  static const Color textWhite = Color(0xFFFFFFFF);
  static const Color textLink = Color(0xFFFF6B7A);

  // ─────────────────────────────────────────────
  // Tag/Chip Colors (대나무숲 감정 태그)
  // ─────────────────────────────────────────────
  static const Color tagExcitement = Color(0xFFFFE4E7); // 두근
  static const Color tagFirstMeet = Color(0xFFE8F5E9); // 첫미팅
  static const Color tagWorry = Color(0xFFFFF3E0); // 고민
  static const Color tagSuccess = Color(0xFFE3F2FD); // 성공후기

  // ─────────────────────────────────────────────
  // Status Colors
  // ─────────────────────────────────────────────
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFFC107);
  static const Color error = Color(0xFFE53935);
  static const Color info = Color(0xFF2196F3);

  // ─────────────────────────────────────────────
  // Border & Divider
  // ─────────────────────────────────────────────
  static const Color borderLight = Color(0xFFEEEEEE);
  static const Color borderMedium = Color(0xFFE0E0E0);
  static const Color divider = Color(0xFFF0F0F0);

  // ─────────────────────────────────────────────
  // Shadow
  // ─────────────────────────────────────────────
  static const Color shadowLight = Color(0x1A000000);
  static const Color shadowMedium = Color(0x29000000);

  // ─────────────────────────────────────────────
  // Bottom Navigation
  // ─────────────────────────────────────────────
  static const Color navActive = Color(0xFFFF6B7A);
  static const Color navInactive = Color(0xFFBDBDBD);

  // ─────────────────────────────────────────────
  // Gradients
  // ─────────────────────────────────────────────
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFFFFFFF), Color(0xFFFFF5F6)],
  );

  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFF6B7A), Color(0xFFFF8A9B)],
  );

  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFE4E7), Color(0xFFE9DFFF)],
  );

  static const LinearGradient mysteryGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFE0E0E0), Color(0xFFBDBDBD)],
  );
}
