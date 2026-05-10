import 'package:flutter/material.dart';

class GlassStamp extends StatelessWidget {
  const GlassStamp({super.key});

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 190,
      height: 190,
      child: CustomPaint(painter: _GlassStampPainter()),
    );
  }
}

class _GlassStampPainter extends CustomPainter {
  const _GlassStampPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final sx = size.width / 190;
    final sy = size.height / 190;

    canvas.save();
    canvas.scale(sx, sy);

    _drawBaseShadow(canvas);
    _drawBase(canvas);
    _drawStem(canvas);
    _drawFacetedHead(canvas);
    _drawHighlights(canvas);

    canvas.restore();
  }

  void _drawBaseShadow(Canvas canvas) {
    final shadow = Paint()
      ..color = const Color(0x1f2d3f46)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    canvas.drawOval(
      Rect.fromCenter(center: const Offset(95, 163), width: 154, height: 32),
      shadow,
    );
  }

  void _drawBase(Canvas canvas) {
    final baseRect = Rect.fromCenter(
      center: const Offset(95, 157),
      width: 176,
      height: 40,
    );

    final sideRect = Rect.fromLTWH(
      baseRect.left,
      baseRect.top + 8,
      baseRect.width,
      27,
    );

    final sidePaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x66ffffff), Color(0x449aa8ac), Color(0x1affffff)],
      ).createShader(sideRect);

    canvas.drawRRect(
      RRect.fromRectAndRadius(sideRect, const Radius.circular(18)),
      sidePaint,
    );

    final topPaint = Paint()
      ..shader = const RadialGradient(
        center: Alignment(-0.28, -0.35),
        radius: 0.72,
        colors: [Color(0xd9ffffff), Color(0x55d7e2e5), Color(0x30808f94)],
      ).createShader(baseRect);

    canvas.drawOval(baseRect, topPaint);

    final rimPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..color = const Color(0x8a809096);

    canvas.drawOval(baseRect.deflate(1), rimPaint);

    final innerRim = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0x99ffffff);

    canvas.drawOval(baseRect.deflate(6), innerRim);
  }

  void _drawStem(Canvas canvas) {
    final stem = Path()
      ..moveTo(67, 135)
      ..cubicTo(73, 116, 73, 91, 62, 67)
      ..cubicTo(69, 72, 121, 72, 128, 67)
      ..cubicTo(117, 91, 117, 116, 123, 135)
      ..cubicTo(113, 144, 77, 144, 67, 135)
      ..close();

    final stemPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
        colors: [
          Color(0x4d5d747d),
          Color(0xb8ffffff),
          Color(0x66d8e5e8),
          Color(0x665d747d),
        ],
        stops: [0, 0.32, 0.68, 1],
      ).createShader(const Rect.fromLTWH(58, 65, 74, 82));

    canvas.drawPath(stem, stemPaint);

    final stemLine = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..color = const Color(0x7c60757c);

    canvas.drawPath(stem, stemLine);

    final footRect = Rect.fromCenter(
      center: const Offset(95, 136),
      width: 72,
      height: 23,
    );

    final footPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x66ffffff), Color(0x996f858c), Color(0x55ffffff)],
      ).createShader(footRect);

    canvas.drawOval(footRect, footPaint);

    final footStroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8
      ..color = const Color(0x7a60757c);

    canvas.drawOval(footRect, footStroke);
  }

  void _drawFacetedHead(Canvas canvas) {
    final body = Path()
      ..moveTo(57, 64)
      ..lineTo(46, 54)
      ..cubicTo(47, 36, 58, 18, 72, 15)
      ..cubicTo(86, 12, 106, 12, 120, 15)
      ..cubicTo(134, 18, 143, 36, 144, 54)
      ..lineTo(133, 64)
      ..cubicTo(116, 72, 74, 72, 57, 64)
      ..close();

    final bodyPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xb8f8fbfb), Color(0x8ad4dde0), Color(0x70a5b2b7)],
      ).createShader(const Rect.fromLTWH(44, 12, 102, 62));

    canvas.drawPath(body, bodyPaint);

    final outline = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.1
      ..strokeJoin = StrokeJoin.round
      ..color = const Color(0x8a6f8188);

    canvas.drawPath(body, outline);

    final capTop = Rect.fromCenter(
      center: const Offset(95, 18),
      width: 66,
      height: 11,
    );

    canvas.drawOval(
      capTop,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0x8affffff), Color(0x2e6f8188)],
        ).createShader(capTop),
    );

    final band = Rect.fromLTWH(51, 57, 88, 15);
    canvas.drawRRect(
      RRect.fromRectAndRadius(band, const Radius.circular(8)),
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0x55ffffff), Color(0x7395a4a9)],
        ).createShader(band),
    );

    final facetPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.3
      ..strokeCap = StrokeCap.round
      ..color = const Color(0x4f6f8188);

    canvas.drawLine(const Offset(57, 64), const Offset(72, 15), facetPaint);
    canvas.drawLine(const Offset(133, 64), const Offset(120, 15), facetPaint);
    canvas.drawLine(const Offset(46, 54), const Offset(144, 54), facetPaint);
  }

  void _drawHighlights(Canvas canvas) {
    final highlight = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.2
      ..strokeCap = StrokeCap.round
      ..color = const Color(0xcfffffff);

    canvas.drawLine(const Offset(74, 45), const Offset(70, 61), highlight);
    canvas.drawLine(const Offset(80, 45), const Offset(76, 62), highlight);
    canvas.drawLine(const Offset(69, 96), const Offset(72, 125), highlight);
    canvas.drawLine(const Offset(61, 151), const Offset(78, 151), highlight);

    final softHighlight = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..color = const Color(0x42ffffff);

    canvas.drawLine(
      const Offset(105, 28),
      const Offset(126, 42),
      softHighlight,
    );
    canvas.drawLine(
      const Offset(111, 83),
      const Offset(116, 124),
      softHighlight,
    );

    final darkEdge = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4
      ..strokeCap = StrokeCap.round
      ..color = const Color(0x66708388);

    canvas.drawLine(const Offset(62, 68), const Offset(70, 134), darkEdge);
    canvas.drawLine(const Offset(128, 68), const Offset(120, 134), darkEdge);
    canvas.drawArc(
      const Rect.fromLTWH(57, 130, 76, 20),
      0.1,
      2.95,
      false,
      darkEdge,
    );
  }

  @override
  bool shouldRepaint(covariant _GlassStampPainter oldDelegate) {
    return false;
  }
}
