import 'package:flutter/material.dart';
import '../matching/matching_screen.dart';
import '../chat/chat_list_screen.dart';
import '../event/event_screen.dart';
import '../community/community_screen.dart';
import '../profile/profile_screen.dart';
import '../../design_system/design_system.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const MatchingScreen(),
    const ChatListScreen(),
    const EventScreen(),
    const CommunityScreen(),
    const ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: SeolBottomNav(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
      ),
    );
  }
}
