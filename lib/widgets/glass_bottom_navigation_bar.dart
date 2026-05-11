import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

enum GlassBottomNavTab { home, community, tutorials, gallery, profile }

class GlassBottomNavigationBar extends StatefulWidget {
  const GlassBottomNavigationBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  static const double _designWidth = 375;
  static const double _navRowHeight = 60;
  static const double _figmaBottomRegion = 0;
  static const double _bottomMargin = 12;
  static const double _horizontalInset = 16;
  static const double _capsuleRadius = 30;
  static const double _activePillWidth = 196;
  static const double _activePillHeight = 104;

  static const Color selectedIconColor = Color(0xFFFF2456);
  static const Color unselectedIconColor = Color(0xFFFF6B8A);
  static const Color labelColor = Colors.black;

  static const _tabs = [
    _GlassNavItemData(
      tab: GlassBottomNavTab.home,
      label: 'Home',
      icon: Icons.home_outlined,
      semanticsLabel: 'Home tab',
    ),
    _GlassNavItemData(
      tab: GlassBottomNavTab.community,
      label: 'Community',
      icon: Icons.auto_awesome_outlined,
      semanticsLabel: 'Community tab',
    ),
    _GlassNavItemData(
      tab: GlassBottomNavTab.tutorials,
      label: 'Tutorials',
      icon: Icons.menu_book_outlined,
      semanticsLabel: 'Tutorials tab',
    ),
    _GlassNavItemData(
      tab: GlassBottomNavTab.gallery,
      label: 'Gallery',
      icon: Icons.grid_view_rounded,
      semanticsLabel: 'Gallery tab',
    ),
    _GlassNavItemData(
      tab: GlassBottomNavTab.profile,
      label: 'Profile',
      icon: Icons.person,
      semanticsLabel: 'Profile tab',
    ),
  ];

  static double totalSafeHeight(BuildContext context) {
    return _navRowHeight + _bottomRegion(context);
  }

  static double _bottomRegion(BuildContext context) {
    return math.max(_figmaBottomRegion, MediaQuery.paddingOf(context).bottom) +
        _bottomMargin;
  }

  @override
  State<GlassBottomNavigationBar> createState() =>
      _GlassBottomNavigationBarState();
}

class _GlassBottomNavigationBarState extends State<GlassBottomNavigationBar> {
  double? _dragCenterX;

  void _handleDragStart(DragStartDetails details) {
    _updateDragCenter(details.globalPosition);
  }

  void _handleDragUpdate(DragUpdateDetails details) {
    _updateDragCenter(details.globalPosition);
  }

  void _handleDragEnd(DragEndDetails details) {
    final nearestIndex = _NavIconCenterSpec.nearestIndex(
      _dragCenterX ?? _NavIconCenterSpec.forIndex(widget.currentIndex),
    );

    if (mounted) {
      setState(() => _dragCenterX = null);
    }
    if (nearestIndex != widget.currentIndex) {
      widget.onTap(nearestIndex);
    }
  }

  void _handleDragCancel() {
    if (mounted) {
      setState(() => _dragCenterX = null);
    }
  }

  void _updateDragCenter(Offset globalPosition) {
    final designX = _designXFromGlobal(globalPosition);
    if (mounted) {
      setState(() => _dragCenterX = designX);
    }
  }

  double _designXFromGlobal(Offset globalPosition) {
    final renderObject = context.findRenderObject();
    if (renderObject is! RenderBox || !renderObject.hasSize) {
      return _NavIconCenterSpec.forIndex(widget.currentIndex);
    }

    final innerWidth = math.max(
      0.0,
      renderObject.size.width - (GlassBottomNavigationBar._horizontalInset * 2),
    );
    final localX =
        renderObject.globalToLocal(globalPosition).dx -
        GlassBottomNavigationBar._horizontalInset;
    final scale = innerWidth / GlassBottomNavigationBar._designWidth;
    if (scale <= 0) {
      return _NavIconCenterSpec.forIndex(widget.currentIndex);
    }

    return (localX / scale)
        .clamp(_NavIconCenterSpec.first, _NavIconCenterSpec.last)
        .toDouble();
  }

  @override
  Widget build(BuildContext context) {
    final bottomRegion = GlassBottomNavigationBar._bottomRegion(context);
    final totalHeight = GlassBottomNavigationBar._navRowHeight + bottomRegion;

    return SizedBox(
      key: const ValueKey('glass_nav_bar'),
      height: totalHeight,
      width: double.infinity,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragStart: _handleDragStart,
        onHorizontalDragUpdate: _handleDragUpdate,
        onHorizontalDragEnd: _handleDragEnd,
        onHorizontalDragCancel: _handleDragCancel,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth;
            final innerWidth = math.max(
              0.0,
              width - (GlassBottomNavigationBar._horizontalInset * 2),
            );
            final scale = innerWidth / GlassBottomNavigationBar._designWidth;
            final pillCenterX =
                GlassBottomNavigationBar._horizontalInset +
                (_dragCenterX ??
                        _NavIconCenterSpec.forIndex(widget.currentIndex)) *
                    scale;
            final pillLeft =
                pillCenterX - (GlassBottomNavigationBar._activePillWidth / 2);

            return Align(
              alignment: Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: GlassBottomNavigationBar._horizontalInset,
                ),
                child: SizedBox(
                  height: GlassBottomNavigationBar._navRowHeight,
                  child: ClipRRect(
                    key: const ValueKey('glass_nav_clip'),
                    borderRadius: BorderRadius.circular(
                      GlassBottomNavigationBar._capsuleRadius,
                    ),
                    child: BackdropFilter(
                      filter: ui.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                      child: Stack(
                        fit: StackFit.expand,
                        clipBehavior: Clip.hardEdge,
                        children: [
                          const _GlassBarBackground(),
                          AnimatedPositioned(
                            key: const ValueKey('glass_nav_active_pill'),
                            duration: _dragCenterX == null
                                ? const Duration(milliseconds: 260)
                                : Duration.zero,
                            curve: Curves.easeOutCubic,
                            left:
                                pillLeft -
                                GlassBottomNavigationBar._horizontalInset,
                            top:
                                (GlassBottomNavigationBar._navRowHeight -
                                    GlassBottomNavigationBar
                                        ._activePillHeight) /
                                2,
                            width: GlassBottomNavigationBar._activePillWidth,
                            height: GlassBottomNavigationBar._activePillHeight,
                            child: const _ActiveGlow(),
                          ),
                          Positioned(
                            top: 0,
                            left: 0,
                            right: 0,
                            height: GlassBottomNavigationBar._navRowHeight,
                            child: Stack(
                              clipBehavior: Clip.none,
                              children: [
                                for (
                                  var index = 0;
                                  index < GlassBottomNavigationBar._tabs.length;
                                  index++
                                )
                                  _PositionedNavItem(
                                    data: GlassBottomNavigationBar._tabs[index],
                                    index: index,
                                    selected: index == widget.currentIndex,
                                    scale: scale,
                                    onTap: widget.onTap,
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _PositionedNavItem extends StatelessWidget {
  const _PositionedNavItem({
    required this.data,
    required this.index,
    required this.selected,
    required this.scale,
    required this.onTap,
  });

  final _GlassNavItemData data;
  final int index;
  final bool selected;
  final double scale;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final frame = _ItemFrameSpec.forIndex(index, selected);

    return Positioned(
      left: frame.left * scale,
      top: 0,
      width: frame.width * scale,
      height: 60,
      child: Semantics(
        button: true,
        selected: selected,
        label: data.semanticsLabel,
        child: Tooltip(
          message: data.label,
          waitDuration: const Duration(milliseconds: 500),
          child: GestureDetector(
            key: ValueKey('glass_nav_item_${data.tab.name}'),
            behavior: HitTestBehavior.opaque,
            onTap: () => onTap(index),
            child: _GlassNavItem(data: data, selected: selected),
          ),
        ),
      ),
    );
  }
}

class _GlassNavItem extends StatelessWidget {
  const _GlassNavItem({required this.data, required this.selected});

  final _GlassNavItemData data;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final color = selected
        ? GlassBottomNavigationBar.selectedIconColor
        : GlassBottomNavigationBar.unselectedIconColor;
    final iconTop = selected ? 10.0 : 18.0;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(height: iconTop),
        _NavIcon(data: data, color: color, selected: selected),
        if (selected)
          SizedBox(
            key: ValueKey('glass_nav_label_${data.tab.name}'),
            height: 26,
            child: Center(
              child: Text(
                data.label,
                maxLines: 1,
                overflow: TextOverflow.visible,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: GlassBottomNavigationBar.labelColor,
                  fontFamily: 'Roboto',
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  height: 24 / 11,
                  letterSpacing: .5,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _NavIcon extends StatelessWidget {
  const _NavIcon({
    required this.data,
    required this.color,
    required this.selected,
  });

  final _GlassNavItemData data;
  final Color color;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    if (data.tab == GlassBottomNavTab.profile) {
      return Container(
        width: 24,
        height: 24,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFFFB6D9), Color(0xFFFFC07E), Color(0xFF7BD6FF)],
          ),
          border: Border.all(color: color, width: 2),
        ),
        child: Icon(Icons.person, color: color, size: 15),
      );
    }

    return Icon(data.icon, color: color, size: 24);
  }
}

class _GlassBarBackground extends StatelessWidget {
  const _GlassBarBackground();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const ValueKey('glass_nav_background'),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: [
            Colors.white.withValues(alpha: .60),
            Colors.white.withValues(alpha: .82),
            Colors.white.withValues(alpha: .78),
            Colors.white.withValues(alpha: .60),
          ],
          stops: const [0, .48, .72, 1],
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.white.withValues(alpha: .18),
            blurRadius: 16,
            spreadRadius: 1,
          ),
          BoxShadow(
            color: Colors.black.withValues(alpha: .10),
            blurRadius: 12,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: CustomPaint(
        key: const ValueKey('glass_nav_grain'),
        painter: _GlassBarBackgroundPainter(),
      ),
    );
  }
}

class _GlassBarBackgroundPainter extends CustomPainter {
  final double grainAlpha = .028;

  @override
  void paint(Canvas canvas, Size size) {
    final grain = Paint()
      ..color = Colors.white.withValues(alpha: grainAlpha)
      ..strokeWidth = 1;
    for (var x = -size.height; x < size.width; x += 11) {
      canvas.drawLine(
        Offset(x.toDouble(), size.height),
        Offset(x + size.height, 0),
        grain,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ActiveGlow extends StatelessWidget {
  const _ActiveGlow();

  @override
  Widget build(BuildContext context) {
    return ImageFiltered(
      imageFilter: ui.ImageFilter.blur(sigmaX: 8, sigmaY: 8),
      child: ShaderMask(
        shaderCallback: (bounds) {
          return const RadialGradient(
            center: Alignment(0, -.05),
            radius: .88,
            colors: [
              Colors.white,
              Color(0xF2FFFFFF),
              Color(0x80FFFFFF),
              Color(0x1FFFFFFF),
              Colors.transparent,
            ],
            stops: [0, .28, .58, .82, 1],
          ).createShader(bounds);
        },
        blendMode: BlendMode.dstIn,
        child: Stack(
          fit: StackFit.expand,
          children: const [
            _GlowBlob(
              alignment: Alignment(-.55, .03),
              color: Color(0xFFD56CBC),
              widthFactor: .7776,
              heightFactor: .9504,
              opacity: 1.00,
            ),
            _GlowBlob(
              alignment: Alignment(-.18, .10),
              color: Color(0xFFF39A4A),
              widthFactor: .8208,
              heightFactor: .9936,
              opacity: 0.40,
            ),
            _GlowBlob(
              alignment: Alignment(.26, -.04),
              color: Color(0xFFE8D83E),
              widthFactor: .8424,
              heightFactor: .9936,
              opacity: 0.38,
            ),
            _GlowBlob(
              alignment: Alignment(.62, -.02),
              color: Color(0xFF76D66F),
              widthFactor: .7776,
              heightFactor: .9504,
              opacity: 0.12,
            ),
          ],
        ),
      ),
    );
  }
}

class _GlowBlob extends StatelessWidget {
  const _GlowBlob({
    required this.alignment,
    required this.color,
    required this.widthFactor,
    required this.heightFactor,
    required this.opacity,
  });

  final Alignment alignment;
  final Color color;
  final double widthFactor;
  final double heightFactor;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: alignment,
      child: FractionallySizedBox(
        widthFactor: widthFactor,
        heightFactor: heightFactor,
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(100),
            gradient: RadialGradient(
              colors: [
                color.withValues(alpha: opacity),
                color.withValues(alpha: opacity * .44),
                color.withValues(alpha: 0),
              ],
              stops: const [0, .48, 1],
            ),
          ),
        ),
      ),
    );
  }
}

class _GlassNavItemData {
  const _GlassNavItemData({
    required this.tab,
    required this.label,
    required this.icon,
    required this.semanticsLabel,
  });

  final GlassBottomNavTab tab;
  final String label;
  final IconData icon;
  final String semanticsLabel;
}

class _NavIconCenterSpec {
  const _NavIconCenterSpec._();

  static const _centers = [37.0, 110.0, 187.0, 262.0, 337.0];
  static const first = 37.0;
  static const last = 337.0;

  static double forIndex(int index) => _centers[index];

  static int nearestIndex(double designX) {
    var nearestIndex = 0;
    var nearestDistance = (designX - _centers[0]).abs();

    for (var index = 1; index < _centers.length; index++) {
      final distance = (designX - _centers[index]).abs();
      if (distance < nearestDistance) {
        nearestIndex = index;
        nearestDistance = distance;
      }
    }

    return nearestIndex;
  }
}

class _ItemFrameSpec {
  const _ItemFrameSpec(this.left, this.width);

  final double left;
  final double width;

  static _ItemFrameSpec forIndex(int index, bool selected) {
    if (selected) {
      return switch (index) {
        0 => const _ItemFrameSpec(-7, 85),
        1 => const _ItemFrameSpec(66, 90),
        2 => const _ItemFrameSpec(145, 83),
        3 => const _ItemFrameSpec(221, 81),
        _ => const _ItemFrameSpec(295, 82),
      };
    }
    return switch (index) {
      0 => const _ItemFrameSpec(-.5, 74),
      1 => const _ItemFrameSpec(70, 80),
      2 => const _ItemFrameSpec(150, 74),
      3 => const _ItemFrameSpec(225, 74),
      _ => const _ItemFrameSpec(300, 74),
    };
  }
}
