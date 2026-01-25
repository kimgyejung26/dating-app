import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';

import '../screens/auth/welcome_screen.dart';
import '../screens/auth/terms_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/auth/student_verification_screen.dart';
import '../screens/auth/initial_setup_screen.dart';
import '../screens/auth/kakao_callback_screen.dart';
import '../screens/main/main_screen.dart';
import '../screens/matching/matching_screen.dart';
import '../screens/chat/chat_list_screen.dart';
import '../screens/event/event_screen.dart';
import '../screens/community/community_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/tutorial/tutorial_screen.dart';

class AppRouter {
  static GoRouter router(AuthProvider authProvider) => GoRouter(
    initialLocation: '/splash', // ✅ 변경
    refreshListenable: authProvider,
    redirect: (context, state) {
      debugPrint(
        '[Router] loc=${state.matchedLocation} '
        'init=${authProvider.isInitialized} '
        'loading=${authProvider.isLoading} '
        'authed=${authProvider.isAuthenticated} '
        'verified=${authProvider.isStudentVerified} '
        'setup=${authProvider.isInitialSetupComplete} '
        'tutorial=${authProvider.hasSeenTutorial}',
      );

      final loc = state.matchedLocation;

      // ✅ 1) 초기화/로딩 중엔 splash로 고정 (핵심)
      if (!authProvider.isInitialized || authProvider.isLoading) {
        return loc == '/splash' ? null : '/splash';
      }

      final isLoggedIn = authProvider.isAuthenticated;
      final isStudentVerified = authProvider.isStudentVerified;
      final isInitialSetupComplete = authProvider.isInitialSetupComplete;
      final hasSeenTutorial = authProvider.hasSeenTutorial;

      final isPublic =
          loc == '/welcome' ||
          loc == '/terms' ||
          loc == '/login' ||
          loc == '/signup' ||
          loc == '/auth/kakao/callback';

      // ✅ 2) 로그인 전: public 외에는 welcome(or login)로
      if (!isLoggedIn) {
        // 앱 정책상 welcome -> terms -> signup 흐름 강제하고 싶으면 welcome으로 보내는 게 깔끔
        if (loc == '/welcome' ||
            loc == '/terms' ||
            loc == '/signup' ||
            loc == '/login')
          return null;
        return '/welcome';
      }

      // ✅ 3) 로그인 후 학생 인증 전: verify로 강제
      if (isLoggedIn && !isStudentVerified) {
        if (loc == '/student-verification' || loc == '/auth/email-link')
          return null;
        return '/student-verification';
      }

      // ✅ 4) 학생 인증 후 초기설정 전: initial-setup으로
      if (isStudentVerified && !isInitialSetupComplete) {
        return loc == '/initial-setup' ? null : '/initial-setup';
      }

      // ✅ 5) 초기설정 후 튜토리얼 안봤으면 튜토리얼로
      if (isInitialSetupComplete && !hasSeenTutorial) {
        return loc == '/tutorial' ? null : '/tutorial';
      }

      // ✅ 6) 다 끝났으면 홈으로, public route 접근 시 홈으로 밀어냄
      if (isInitialSetupComplete && hasSeenTutorial) {
        if (isPublic ||
            loc == '/tutorial' ||
            loc == '/initial-setup' ||
            loc == '/student-verification') {
          return '/home';
        }
      }

      return null;
    },
    routes: [
      // ✅ Splash 추가
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),

      // Auth Flow
      GoRoute(
        path: '/welcome',
        name: 'welcome',
        builder: (_, __) => const WelcomeScreen(),
      ),
      GoRoute(
        path: '/terms',
        name: 'terms',
        builder: (_, __) => const TermsScreen(),
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (_, __) => const SignupScreen(),
      ),
      GoRoute(
        path: '/signup',
        name: 'signup',
        builder: (_, __) => const SignupScreen(),
      ),
      GoRoute(
        path: '/auth/kakao/callback',
        name: 'kakao-callback',
        builder: (_, __) => const KakaoCallbackScreen(),
      ),
      GoRoute(
        path: '/auth/email-link',
        name: 'email-link',
        builder: (_, __) => const StudentVerificationScreen(),
      ),
      GoRoute(
        path: '/student-verification',
        name: 'student-verification',
        builder: (_, __) => const StudentVerificationScreen(),
      ),
      GoRoute(
        path: '/initial-setup',
        name: 'initial-setup',
        builder: (_, __) => const InitialSetupScreen(),
      ),

      // Tutorial
      GoRoute(
        path: '/tutorial',
        name: 'tutorial',
        builder: (_, __) => const TutorialScreen(),
      ),

      // Main
      GoRoute(
        path: '/home',
        name: 'home',
        builder: (_, __) => const MainScreen(),
      ),
      GoRoute(
        path: '/main',
        name: 'main',
        builder: (_, __) => const MainScreen(),
        routes: [
          GoRoute(
            path: 'matching',
            name: 'matching',
            builder: (_, __) => const MatchingScreen(),
          ),
          GoRoute(
            path: 'chat',
            name: 'chat',
            builder: (_, __) => const ChatListScreen(),
          ),
          GoRoute(
            path: 'event',
            name: 'event',
            builder: (_, __) => const EventScreen(),
          ),
          GoRoute(
            path: 'community',
            name: 'community',
            builder: (_, __) => const CommunityScreen(),
          ),
          GoRoute(
            path: 'profile',
            name: 'profile',
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
