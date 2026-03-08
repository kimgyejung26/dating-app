import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'router/app_router.dart';
import 'router/route_names.dart';

/// 설레연 앱 (MaterialApp 루트 + Cupertino UI 유지)
/// MaterialLocalizations 제공을 위해 MaterialApp 사용
class SeolleyeonApp extends StatelessWidget {
  const SeolleyeonApp({super.key});

  // 앱 전체에서 사용할 프라이머리 컬러
  static const Color primaryColor = Color(0xFFFF6B8A);
  static const Color backgroundColor = Color(0xFFFAFAFA);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '설레연',
      debugShowCheckedModeBanner: false,
      // Material 테마 (Cupertino 스타일 유지)
      theme: ThemeData(
        useMaterial3: true,
        primaryColor: primaryColor,
        fontFamily: GoogleFonts.notoSansKr().fontFamily ?? 'Noto Sans KR',
        textTheme: _textThemeWithoutUnderline(
          GoogleFonts.notoSansKrTextTheme(
            ThemeData.light().textTheme,
          ),
        ),
        colorScheme: ColorScheme.light(
          primary: primaryColor,
          secondary: primaryColor,
          surface: backgroundColor,
        ),
        scaffoldBackgroundColor: backgroundColor,
        appBarTheme: const AppBarTheme(
          backgroundColor: backgroundColor,
          foregroundColor: Color(0xFF0F172A),
          elevation: 0,
        ),
        // Cupertino 스타일 오버라이드
        cupertinoOverrideTheme: const CupertinoThemeData(
          primaryColor: primaryColor,
          brightness: Brightness.light,
          scaffoldBackgroundColor: backgroundColor,
        ),
        // iOS 스타일 페이지 전환
        pageTransitionsTheme: const PageTransitionsTheme(
          builders: {
            TargetPlatform.android: CupertinoPageTransitionsBuilder(),
            TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          },
        ),
      ),
      initialRoute: RouteNames.splash,
      onGenerateRoute: AppRouter.generateRoute,
      builder: (context, child) {
        final theme = Theme.of(context);
        final fallback = theme.textTheme.bodyMedium ?? const TextStyle(decoration: TextDecoration.none);
        return DefaultTextStyle(
          style: fallback.copyWith(decoration: TextDecoration.none),
          child: child!,
        );
      },
    );
  }
}

/// 텍스트 테마 전체에 밑줄 제거 적용 (노란 밑줄 경고 방지)
TextTheme _textThemeWithoutUnderline(TextTheme base) {
  TextStyle noUnderline(TextStyle? s) =>
      s == null ? const TextStyle(decoration: TextDecoration.none) : s.copyWith(decoration: TextDecoration.none);
  return TextTheme(
    displayLarge: noUnderline(base.displayLarge),
    displayMedium: noUnderline(base.displayMedium),
    displaySmall: noUnderline(base.displaySmall),
    headlineLarge: noUnderline(base.headlineLarge),
    headlineMedium: noUnderline(base.headlineMedium),
    headlineSmall: noUnderline(base.headlineSmall),
    titleLarge: noUnderline(base.titleLarge),
    titleMedium: noUnderline(base.titleMedium),
    titleSmall: noUnderline(base.titleSmall),
    bodyLarge: noUnderline(base.bodyLarge),
    bodyMedium: noUnderline(base.bodyMedium),
    bodySmall: noUnderline(base.bodySmall),
    labelLarge: noUnderline(base.labelLarge),
    labelMedium: noUnderline(base.labelMedium),
    labelSmall: noUnderline(base.labelSmall),
  );
}
