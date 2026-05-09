import 'package:flutter/material.dart';

class AppColors {
  // Primary Colors
  static const Color primaryPink = Color(0xFFFF69B4); // 핫핑크
  static const Color primaryPinkLight = Color(0xFFFFB6C1); // 연한 핑크
  static const Color primaryPinkDark = Color(0xFFE91E63); // 진한 핑크
  
  // Secondary Colors
  static const Color secondaryPurple = Color(0xFF9C27B0);
  static const Color secondaryPurpleLight = Color(0xFFE1BEE7);
  
  // Background Colors
  static const Color backgroundWhite = Color(0xFFFFFFFF);
  static const Color backgroundLight = Color(0xFFF5F5F5);
  static const Color backgroundGrey = Color(0xFFF0F0F0);
  
  // Text Colors
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color textTertiary = Color(0xFF9E9E9E);
  static const Color textWhite = Color(0xFFFFFFFF);
  
  // Accent Colors
  static const Color accentGreen = Color(0xFF4CAF50);
  static const Color accentRed = Color(0xFFF44336);
  static const Color accentYellow = Color(0xFFFFC107);
  static const Color accentBlue = Color(0xFF2196F3);
  
  // Status Colors
  static const Color onlineGreen = Color(0xFF4CAF50);
  static const Color offlineGrey = Color(0xFF9E9E9E);
  
  // Border Colors
  static const Color borderLight = Color(0xFFE0E0E0);
  static const Color borderMedium = Color(0xFFBDBDBD);
  
  // Gradient Colors
  static const LinearGradient pinkGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFF69B4), Color(0xFFFFB6C1)],
  );
  
  static const LinearGradient purpleGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF9C27B0), Color(0xFFE1BEE7)],
  );
}
