// =============================================================================
// Glass Bottom Navigation Bar — Demo / Preview Screen
// =============================================================================
//
// Self-contained demo that shows all three variants with light/dark toggle,
// label toggle, badge examples, and avatar tab example.
//
// Navigate here via RouteNames or push it manually:
//   Navigator.push(context, CupertinoPageRoute(
//     builder: (_) => const GlassBottomNavDemoScreen(),
//   ));
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../glass_bottom_nav/glass_bottom_nav_bar.dart';

class GlassBottomNavDemoScreen extends StatefulWidget {
  const GlassBottomNavDemoScreen({super.key});

  @override
  State<GlassBottomNavDemoScreen> createState() =>
      _GlassBottomNavDemoScreenState();
}

class _GlassBottomNavDemoScreenState extends State<GlassBottomNavDemoScreen> {
  int _currentVariantIndex = 0;
  int _selectedTab = 0;
  bool _showLabels = true;
  bool _isDark = true;

  final _variants = GlassNavVariant.values;

  String get _variantLabel {
    switch (_variants[_currentVariantIndex]) {
      case GlassNavVariant.softLight:
        return 'softLight';
      case GlassNavVariant.darkLens:
        return 'darkLens';
      case GlassNavVariant.darkMinimal:
        return 'darkMinimal';
    }
  }

  List<GlassNavItem> get _items => [
        GlassNavItem(
          icon: CupertinoIcons.heart,
          activeIcon: CupertinoIcons.heart_fill,
          label: '설레연',
        ),
        GlassNavItem(
          icon: CupertinoIcons.chat_bubble,
          activeIcon: CupertinoIcons.chat_bubble_fill,
          label: '채팅',
          badgeCount: 3,
        ),
        GlassNavItem(
          icon: CupertinoIcons.calendar,
          activeIcon: CupertinoIcons.calendar_today,
          label: '이벤트',
        ),
        GlassNavItem(
          icon: CupertinoIcons.tree,
          activeIcon: CupertinoIcons.tree,
          label: '대나무숲',
          showDot: true,
        ),
        GlassNavItem(
          icon: CupertinoIcons.person,
          activeIcon: CupertinoIcons.person_fill,
          label: '내 페이지',
        ),
      ];

  // items without labels
  List<GlassNavItem> get _iconOnlyItems => [
        GlassNavItem(
          icon: CupertinoIcons.house,
          activeIcon: CupertinoIcons.house_fill,
        ),
        GlassNavItem(
          icon: CupertinoIcons.play_rectangle,
          activeIcon: CupertinoIcons.play_rectangle_fill,
        ),
        GlassNavItem(
          icon: CupertinoIcons.paperplane,
          activeIcon: CupertinoIcons.paperplane_fill,
          showDot: true,
        ),
        GlassNavItem(
          icon: CupertinoIcons.search,
          activeIcon: CupertinoIcons.search,
        ),
        GlassNavItem(
          icon: CupertinoIcons.person_circle,
          activeIcon: CupertinoIcons.person_circle_fill,
          // Could use avatarImage here in production
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final currentVariant = _variants[_currentVariantIndex];
    final bg = _isDark
        ? const Color(0xFF121214)
        : const Color(0xFFF3EEF8);

    return Theme(
      data: _isDark ? ThemeData.dark() : ThemeData.light(),
      child: CupertinoPageScaffold(
        backgroundColor: bg,
        child: Stack(
          children: [
            // ── Background decoration ──
            _DemoBackground(isDark: _isDark),

            // ── Controls ──
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          CupertinoIcons.layers_alt_fill,
                          color: _isDark
                              ? const Color(0xFFF0E8ED)
                              : const Color(0xFF1C1440),
                          size: 22,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Glass Nav Demo',
                          style: TextStyle(
                            fontFamily: 'Pretendard',
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            color: _isDark
                                ? const Color(0xFFF0E8ED)
                                : const Color(0xFF1C1440),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 28),

                    // Variant selector
                    _ControlRow(
                      isDark: _isDark,
                      label: 'Variant',
                      value: _variantLabel,
                      onNext: () => setState(() {
                        _currentVariantIndex =
                            (_currentVariantIndex + 1) % _variants.length;
                      }),
                    ),
                    const SizedBox(height: 16),

                    // Dark mode toggle
                    _ToggleRow(
                      isDark: _isDark,
                      label: 'Dark mode',
                      value: _isDark,
                      onChanged: (v) => setState(() => _isDark = v),
                    ),
                    const SizedBox(height: 12),

                    // Labels toggle
                    _ToggleRow(
                      isDark: _isDark,
                      label: 'Show labels',
                      value: _showLabels,
                      onChanged: (v) => setState(() => _showLabels = v),
                    ),
                    const SizedBox(height: 28),

                    // Info
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: _isDark
                            ? const Color(0x18FFFFFF)
                            : const Color(0x0A000000),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _isDark
                              ? const Color(0x15FFFFFF)
                              : const Color(0x10000000),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '현재 탭: ${_selectedTab + 1} / ${_showLabels ? _items.length : _iconOnlyItems.length}',
                            style: TextStyle(
                              fontFamily: 'Pretendard',
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: _isDark
                                  ? const Color(0xFFB0A0AC)
                                  : const Color(0xFF666666),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Tap the nav bar items below. Notice the smooth capsule animation, badge indicators, and variant differences.',
                            style: TextStyle(
                              fontFamily: 'Pretendard',
                              fontSize: 12,
                              color: _isDark
                                  ? const Color(0xFF7A6B76)
                                  : const Color(0xFFAAAAAA),
                              height: 1.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // ── Navigation bar ──
            GlassBottomNavPositioned(
              items: _showLabels ? _items : _iconOnlyItems,
              currentIndex: _selectedTab.clamp(
                0,
                (_showLabels ? _items.length : _iconOnlyItems.length) - 1,
              ),
              variant: currentVariant,
              showLabels: _showLabels,
              onTap: (i) => setState(() => _selectedTab = i),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Demo background ─────────────────────────────────────────────────────────

class _DemoBackground extends StatelessWidget {
  final bool isDark;
  const _DemoBackground({required this.isDark});

  @override
  Widget build(BuildContext context) {
    if (isDark) {
      return Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF1C1520),
              Color(0xFF121214),
              Color(0xFF181420),
            ],
          ),
        ),
        child: Stack(
          children: [
            // Ambient light blobs
            Positioned(
              top: -60,
              left: -40,
              child: Container(
                width: 200,
                height: 200,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      const Color(0xFFFF6B8A).withValues(alpha: 0.06),
                      const Color(0x00000000),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: 120,
              right: -30,
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      const Color(0xFF8B5CF6).withValues(alpha: 0.05),
                      const Color(0x00000000),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFF8F0FF),
            Color(0xFFF3EEF8),
            Color(0xFFFFEFF3),
          ],
        ),
      ),
    );
  }
}

// ─── Control widgets ─────────────────────────────────────────────────────────

class _ControlRow extends StatelessWidget {
  final bool isDark;
  final String label;
  final String value;
  final VoidCallback onNext;

  const _ControlRow({
    required this.isDark,
    required this.label,
    required this.value,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    final fg =
        isDark ? const Color(0xFFF0E8ED) : const Color(0xFF1C1440);
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: fg,
          ),
        ),
        CupertinoButton(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          onPressed: onNext,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: isDark
                  ? const Color(0x20FFFFFF)
                  : const Color(0x0C000000),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontFamily: 'Pretendard',
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: fg,
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  CupertinoIcons.chevron_right,
                  size: 14,
                  color: fg.withValues(alpha: 0.5),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ToggleRow extends StatelessWidget {
  final bool isDark;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _ToggleRow({
    required this.isDark,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final fg =
        isDark ? const Color(0xFFF0E8ED) : const Color(0xFF1C1440);
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: fg,
          ),
        ),
        CupertinoSwitch(
          value: value,
          activeTrackColor: const Color(0xFFFF6B8A),
          onChanged: onChanged,
        ),
      ],
    );
  }
}
