import 'package:go_router/go_router.dart';
import '../screens/auth/welcome_screen.dart';
import '../screens/auth/terms_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/auth/student_verification_screen.dart';
import '../screens/auth/initial_setup_screen.dart';
import '../screens/main/main_screen.dart';
import '../screens/matching/matching_screen.dart';
import '../screens/chat/chat_list_screen.dart';
import '../screens/event/event_screen.dart';
import '../screens/community/community_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/tutorial/tutorial_screen.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: '/welcome',
    routes: [
      // Auth Flow
      GoRoute(
        path: '/welcome',
        name: 'welcome',
        builder: (context, state) => const WelcomeScreen(),
      ),
      GoRoute(
        path: '/terms',
        name: 'terms',
        builder: (context, state) => const TermsScreen(),
      ),
      GoRoute(
        path: '/signup',
        name: 'signup',
        builder: (context, state) => const SignupScreen(),
      ),
      GoRoute(
        path: '/student-verification',
        name: 'student-verification',
        builder: (context, state) => const StudentVerificationScreen(),
      ),
      GoRoute(
        path: '/initial-setup',
        name: 'initial-setup',
        builder: (context, state) => const InitialSetupScreen(),
      ),
      
      // Tutorial
      GoRoute(
        path: '/tutorial',
        name: 'tutorial',
        builder: (context, state) => const TutorialScreen(),
      ),
      
      // Main App (with bottom navigation)
      GoRoute(
        path: '/main',
        name: 'main',
        builder: (context, state) => const MainScreen(),
        routes: [
          GoRoute(
            path: 'matching',
            name: 'matching',
            builder: (context, state) => const MatchingScreen(),
          ),
          GoRoute(
            path: 'chat',
            name: 'chat',
            builder: (context, state) => const ChatListScreen(),
          ),
          GoRoute(
            path: 'event',
            name: 'event',
            builder: (context, state) => const EventScreen(),
          ),
          GoRoute(
            path: 'community',
            name: 'community',
            builder: (context, state) => const CommunityScreen(),
          ),
          GoRoute(
            path: 'profile',
            name: 'profile',
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
}
