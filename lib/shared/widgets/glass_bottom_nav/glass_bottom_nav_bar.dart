// =============================================================================
// Glass Bottom Navigation Bar — Main Widget
// =============================================================================
//
// A floating, glassmorphism bottom navigation bar with an animated active
// capsule/lens overlay. Supports 3 visual variants out of the box and is
// fully customisable via [GlassNavStyle].
//
// Usage:
//   GlassBottomNavBar(
//     items: [...],
//     currentIndex: _index,
//     onTap: (i) => setState(() => _index = i),
//     variant: GlassNavVariant.softLight,
//   )
// =============================================================================

import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

import 'glass_bottom_nav_item.dart';
import 'glass_bottom_nav_tokens.dart';

// ─── Public barrel export ────────────────────────────────────────────────────

export 'glass_bottom_nav_item.dart';
export 'glass_bottom_nav_tokens.dart';

// ─── Main widget ─────────────────────────────────────────────────────────────

class GlassBottomNavBar extends StatefulWidget {
  /// Tab descriptors. Length must be ≥ 2.
  final List<GlassNavItem> items;

  /// Currently selected index. Must be in `[0, items.length)`.
  final int currentIndex;

  /// Called when a tab is tapped.
  final ValueChanged<int>? onTap;

  /// Visual preset. Overridden by [style] if provided.
  final GlassNavVariant variant;

  /// Fully custom style. Takes precedence over [variant].
  final GlassNavStyle? style;

  /// Whether to render text labels beneath icons.
  final bool showLabels;

  const GlassBottomNavBar({
    super.key,
    required this.items,
    required this.currentIndex,
    this.onTap,
    this.variant = GlassNavVariant.darkLens,
    this.style,
    this.showLabels = true,
  }) : assert(items.length >= 2);

  @override
  State<GlassBottomNavBar> createState() => _GlassBottomNavBarState();
}

class _GlassBottomNavBarState extends State<GlassBottomNavBar>
    with SingleTickerProviderStateMixin {
  late GlassNavStyle _s;

  @override
  void didUpdateWidget(covariant GlassBottomNavBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    _s = widget.style ?? GlassNavStyle.fromVariant(widget.variant);
  }

  @override
  void initState() {
    super.initState();
    _s = widget.style ?? GlassNavStyle.fromVariant(widget.variant);
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  double _barWidth(double screenWidth) =>
      screenWidth * _s.barWidthFraction;

  double _horizontalMargin(double screenWidth) =>
      (screenWidth - _barWidth(screenWidth)) / 2;

  double _slotWidth(double barWidth) =>
      barWidth / widget.items.length;

  double _capsuleWidth(double barWidth) {
    final slotW = _slotWidth(barWidth);
    // Capsule is slightly narrower than the slot so it doesn't touch siblings.
    return math.min(slotW - 6, _s.capsuleHeight * 1.6);
  }

  double _capsuleLeft(double barWidth) {
    final slotW = _slotWidth(barWidth);
    final cw = _capsuleWidth(barWidth);
    return slotW * widget.currentIndex + (slotW - cw) / 2;
  }

  // ── build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final screenW = MediaQuery.of(context).size.width;
    final bottomPad = MediaQuery.of(context).padding.bottom;
    final barW = _barWidth(screenW);
    final hMargin = _horizontalMargin(screenW);

    return Positioned(
      left: hMargin,
      right: hMargin,
      bottom: bottomPad + _s.bottomMargin,
      height: _s.barHeight + (_s.capsuleVerticalOffset < 0 ? -_s.capsuleVerticalOffset : 0),
      child: RepaintBoundary(
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            // 1️⃣ Bar body ──────────────────────────────────────────────────
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              height: _s.barHeight,
              child: _BarBody(style: _s),
            ),

            // 2️⃣ Active capsule ────────────────────────────────────────────
            AnimatedPositioned(
              duration: _s.animDuration,
              curve: _s.animCurve,
              left: _capsuleLeft(barW),
              bottom: (_s.barHeight - _s.capsuleHeight) / 2 + (-_s.capsuleVerticalOffset),
              width: _capsuleWidth(barW),
              height: _s.capsuleHeight,
              child: _ActiveCapsule(style: _s),
            ),

            // 3️⃣ Items row ────────────────────────────────────────────────
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              height: _s.barHeight,
              child: Row(
                children: List.generate(widget.items.length, (i) {
                  return Expanded(
                    child: _NavItemWidget(
                      item: widget.items[i],
                      isActive: i == widget.currentIndex,
                      showLabel: widget.showLabels,
                      style: _s,
                      onTap: () {
                        HapticFeedback.selectionClick();
                        widget.onTap?.call(i);
                      },
                    ),
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Convenience positioned wrapper ──────────────────────────────────────────

/// Drop-in replacement that wraps [GlassBottomNavBar] inside a [Positioned]
/// widget for easy use inside a [Stack].
///
/// ```dart
/// Stack(children: [
///   // …content…
///   GlassBottomNavPositioned(
///     items: [...],
///     currentIndex: _i,
///     onTap: (i) => setState(() => _i = i),
///   ),
/// ]);
/// ```
class GlassBottomNavPositioned extends StatelessWidget {
  final List<GlassNavItem> items;
  final int currentIndex;
  final ValueChanged<int>? onTap;
  final GlassNavVariant variant;
  final GlassNavStyle? style;
  final bool showLabels;

  const GlassBottomNavPositioned({
    super.key,
    required this.items,
    required this.currentIndex,
    this.onTap,
    this.variant = GlassNavVariant.darkLens,
    this.style,
    this.showLabels = true,
  });

  @override
  Widget build(BuildContext context) {
    final s = style ?? GlassNavStyle.fromVariant(variant);
    final screenW = MediaQuery.of(context).size.width;
    final barW = screenW * s.barWidthFraction;
    final hMargin = (screenW - barW) / 2;
    final bottomPad = MediaQuery.of(context).padding.bottom;
    final extraTop = s.capsuleVerticalOffset < 0 ? -s.capsuleVerticalOffset : 0.0;

    return Positioned(
      left: hMargin,
      right: hMargin,
      bottom: bottomPad + s.bottomMargin,
      height: s.barHeight + extraTop,
      child: RepaintBoundary(
        child: _GlassNavContent(
          items: items,
          currentIndex: currentIndex,
          onTap: onTap,
          style: s,
          showLabels: showLabels,
          barWidth: barW,
        ),
      ),
    );
  }
}

// ─── Inner content (shared between GlassBottomNavBar & Positioned) ───────────

class _GlassNavContent extends StatelessWidget {
  final List<GlassNavItem> items;
  final int currentIndex;
  final ValueChanged<int>? onTap;
  final GlassNavStyle style;
  final bool showLabels;
  final double barWidth;

  const _GlassNavContent({
    required this.items,
    required this.currentIndex,
    this.onTap,
    required this.style,
    required this.showLabels,
    required this.barWidth,
  });

  double _slotWidth() => barWidth / items.length;

  double _capsuleWidth() {
    final slotW = _slotWidth();
    return math.min(slotW - 6, style.capsuleHeight * 1.6);
  }

  double _capsuleLeft() {
    final slotW = _slotWidth();
    final cw = _capsuleWidth();
    return slotW * currentIndex + (slotW - cw) / 2;
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        // 1️⃣ Bar body
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          height: style.barHeight,
          child: _BarBody(style: style),
        ),

        // 2️⃣ Active capsule
        AnimatedPositioned(
          duration: style.animDuration,
          curve: style.animCurve,
          left: _capsuleLeft(),
          bottom: (style.barHeight - style.capsuleHeight) / 2 +
              (-style.capsuleVerticalOffset),
          width: _capsuleWidth(),
          height: style.capsuleHeight,
          child: _ActiveCapsule(style: style),
        ),

        // 3️⃣ Items row
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          height: style.barHeight,
          child: Row(
            children: List.generate(items.length, (i) {
              return Expanded(
                child: _NavItemWidget(
                  item: items[i],
                  isActive: i == currentIndex,
                  showLabel: showLabels,
                  style: style,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    onTap?.call(i);
                  },
                ),
              );
            }),
          ),
        ),
      ],
    );
  }
}

// ─── Bar body (glass surface) ────────────────────────────────────────────────

class _BarBody extends StatelessWidget {
  final GlassNavStyle style;
  const _BarBody({required this.style});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(style.barRadius),
        boxShadow: style.barShadow,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(style.barRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: style.blurSigma,
            sigmaY: style.blurSigma,
          ),
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  style.barColor,
                  style.barGradientEnd ?? style.barColor,
                ],
              ),
              borderRadius: BorderRadius.circular(style.barRadius),
              border: Border.all(
                color: style.borderColor,
                width: 1,
              ),
            ),
            // Inner top highlight
            child: Align(
              alignment: Alignment.topCenter,
              child: Container(
                height: style.barHeight * style.innerHighlightHeight,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(style.barRadius),
                  ),
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      style.innerHighlightColor,
                      style.innerHighlightColor.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Active capsule / lens ──────────────────────────────────────────────────

class _ActiveCapsule extends StatelessWidget {
  final GlassNavStyle style;
  const _ActiveCapsule({required this.style});

  @override
  Widget build(BuildContext context) {
    Widget capsule = Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            style.capsuleColor,
            style.capsuleGradientEnd ?? style.capsuleColor,
          ],
        ),
        borderRadius: BorderRadius.circular(style.capsuleRadius),
        border: Border.all(color: style.capsuleBorder, width: 1),
        boxShadow: style.capsuleShadow,
      ),
    );

    // Optional capsule-level blur
    if (style.capsuleBlurSigma > 0) {
      capsule = ClipRRect(
        borderRadius: BorderRadius.circular(style.capsuleRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: style.capsuleBlurSigma,
            sigmaY: style.capsuleBlurSigma,
          ),
          child: capsule,
        ),
      );
    }

    // Optional chromatic fringe (dark variants only)
    if (style.capsuleChromaticFringe) {
      capsule = CustomPaint(
        painter: _ChromaticFringePainter(
          radius: style.capsuleRadius,
        ),
        child: capsule,
      );
    }

    return AnimatedContainer(
      duration: style.animDuration,
      curve: style.animCurve,
      child: capsule,
    );
  }
}

/// Extremely subtle rainbow/chromatic fringe around capsule edges.
class _ChromaticFringePainter extends CustomPainter {
  final double radius;
  _ChromaticFringePainter({required this.radius});

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(radius));

    final paint = Paint()
      ..shader = SweepGradient(
        colors: const [
          Color(0x08FF6B8A),
          Color(0x06A78BFA),
          Color(0x0634D399),
          Color(0x08FED941),
          Color(0x08FF6B8A),
        ],
      ).createShader(rect)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    canvas.drawRRect(rrect, paint);
  }

  @override
  bool shouldRepaint(covariant _ChromaticFringePainter old) =>
      old.radius != radius;
}

// ─── Single nav item ─────────────────────────────────────────────────────────

class _NavItemWidget extends StatelessWidget {
  final GlassNavItem item;
  final bool isActive;
  final bool showLabel;
  final GlassNavStyle style;
  final VoidCallback onTap;

  const _NavItemWidget({
    required this.item,
    required this.isActive,
    required this.showLabel,
    required this.style,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final iconColor =
        isActive ? style.iconColorActive : style.iconColorInactive;
    final labelColor =
        isActive ? style.labelColorActive : style.labelColorInactive;
    final iconSize =
        isActive ? style.iconSizeActive : style.iconSizeInactive;
    final labelWeight =
        isActive ? style.labelWeightActive : style.labelWeightInactive;
    final effectiveIcon =
        isActive ? (item.activeIcon ?? item.icon) : item.icon;

    return Semantics(
      label: item.semanticsLabel ?? item.label,
      button: true,
      selected: isActive,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // ── Icon or avatar ──
              Stack(
                clipBehavior: Clip.none,
                children: [
                  // Icon / Avatar
                  if (item.avatarImage != null)
                    _AvatarIcon(
                      image: item.avatarImage!,
                      size: iconSize,
                      isActive: isActive,
                      activeColor: style.iconColorActive,
                    )
                  else
                    AnimatedDefaultTextStyle(
                      style: TextStyle(fontSize: iconSize, color: iconColor),
                      duration: style.animDuration,
                      child: AnimatedScale(
                        scale: isActive ? 1.0 : 0.92,
                        duration: style.animDuration,
                        curve: style.animCurve,
                        child: Icon(
                          effectiveIcon,
                          size: iconSize,
                          color: iconColor,
                        ),
                      ),
                    ),

                  // Badge
                  if (item.badgeCount > 0)
                    Positioned(
                      right: -6,
                      top: -4,
                      child: _CountBadge(
                        count: item.badgeCount,
                        bgColor: style.badgeCountBg,
                        fgColor: style.badgeCountFg,
                        size: style.badgeCountSize,
                      ),
                    )
                  else if (item.showDot)
                    Positioned(
                      right: -2,
                      top: -2,
                      child: Container(
                        width: style.badgeDotSize,
                        height: style.badgeDotSize,
                        decoration: BoxDecoration(
                          color: style.badgeDotColor,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color:
                                  style.badgeDotColor.withValues(alpha: 0.4),
                              blurRadius: 4,
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),

              // ── Label ──
              if (showLabel && item.label != null) ...[
                SizedBox(height: style.iconLabelGap),
                AnimatedDefaultTextStyle(
                  style: TextStyle(
                    fontFamily: 'Pretendard',
                    fontSize: style.labelSize,
                    fontWeight: labelWeight,
                    color: labelColor,
                    letterSpacing: -0.2,
                  ),
                  duration: style.animDuration,
                  child: Text(
                    item.label!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Avatar icon ─────────────────────────────────────────────────────────────

class _AvatarIcon extends StatelessWidget {
  final ImageProvider image;
  final double size;
  final bool isActive;
  final Color activeColor;

  const _AvatarIcon({
    required this.image,
    required this.size,
    required this.isActive,
    required this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: size + 4,
      height: size + 4,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: isActive ? activeColor : const Color(0x00000000),
          width: 2,
        ),
      ),
      child: ClipOval(
        child: Image(
          image: image,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => Icon(
            CupertinoIcons.person_fill,
            size: size * 0.7,
            color: const Color(0xFF8E8E93),
          ),
        ),
      ),
    );
  }
}

// ─── Count badge ─────────────────────────────────────────────────────────────

class _CountBadge extends StatelessWidget {
  final int count;
  final Color bgColor;
  final Color fgColor;
  final double size;

  const _CountBadge({
    required this.count,
    required this.bgColor,
    required this.fgColor,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    final text = count > 99 ? '99+' : count.toString();
    return Container(
      height: size,
      constraints: BoxConstraints(minWidth: size),
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(size / 2),
        boxShadow: [
          BoxShadow(
            color: bgColor.withValues(alpha: 0.4),
            blurRadius: 4,
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        text,
        style: TextStyle(
          fontFamily: 'Pretendard',
          fontSize: size * 0.6,
          fontWeight: FontWeight.w700,
          color: fgColor,
          height: 1,
        ),
      ),
    );
  }
}
