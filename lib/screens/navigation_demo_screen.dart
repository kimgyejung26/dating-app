import 'package:flutter/material.dart';

import '../widgets/glass_bottom_navigation_bar.dart';

class NavigationDemoScreen extends StatefulWidget {
  const NavigationDemoScreen({super.key});

  @override
  State<NavigationDemoScreen> createState() => _NavigationDemoScreenState();
}

class _NavigationDemoScreenState extends State<NavigationDemoScreen> {
  int _selectedIndex = 0;

  static const _titles = [
    'Home',
    'Community',
    'Tutorials',
    'Gallery',
    'Profile',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.25,
            colors: [Color(0xFF343434), Color(0xFF1E1E1E), Color(0xFF111111)],
            stops: [0, .58, 1],
          ),
        ),
        child: IndexedStack(
          index: _selectedIndex,
          children: [
            for (final title in _titles)
              _DemoTabPage(
                title: title,
                bottomPadding: GlassBottomNavigationBar.totalSafeHeight(
                  context,
                ),
              ),
          ],
        ),
      ),
      bottomNavigationBar: GlassBottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
      ),
    );
  }
}

class _DemoTabPage extends StatelessWidget {
  const _DemoTabPage({required this.title, required this.bottomPadding});

  final String title;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(24, 32, 24, bottomPadding + 24),
      child: Align(
        alignment: Alignment.bottomLeft,
        child: Text(
          title,
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
            color: Colors.white.withValues(alpha: .9),
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}
