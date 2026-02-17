// =============================================================================
// 프로필 사진 등록 화면 (온보딩 Step 4)
// 경로: lib/features/onboarding/screens/photo_upload_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const PhotoUploadScreen()),
// );
// =============================================================================

import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFEF3976);
  static const Color backgroundLight = Color(0xFFF8F6F6);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color textMain = Color(0xFF181113);
  static const Color textSub = Color(0xFF89616F);
  static const Color textGray = Color(0xFF9CA3AF);
  static const Color borderDashed = Color(0xFFE6DBDF);
  static const Color progressBg = Color(0xFFE6DBDF);
}

// =============================================================================
// 메인 화면
// =============================================================================
class PhotoUploadScreen extends StatefulWidget {
  final int currentStep;
  final int totalSteps;
  final VoidCallback? onBack;
  final Function(List<String> photos)? onNext;

  const PhotoUploadScreen({
    super.key,
    this.currentStep = 5,
    this.totalSteps = 8,
    this.onBack,
    this.onNext,
  });

  @override
  State<PhotoUploadScreen> createState() => _PhotoUploadScreenState();
}

class _PhotoUploadScreenState extends State<PhotoUploadScreen> {
  // 초기 더미 데이터 (HTML 예시 반영)
  final List<String?> _photos = [
    'https://lh3.googleusercontent.com/aida-public/AB6AXuD-ahgOxjDASwoIQylq-wRkziL385-3iWMgRMD_38gGtXlc0Lk5Yxs7oV7Qd2DIq8fBYJYO2twuahC5Q6vqtcYZ5Gd_iypFUS_K5q1F0WFgxgcBsJ4Qe_972QxVV2pbb4sU_y0UVckr4ax4CLNR-DWY9QdBnovKApjHoNuUQ3bFRa5FIE3-KGGVR3QqXEfEY3CsXUMmwYnsDtyUzv1UwYVdPHka9yGc68VNDMBQVpQpbYuA8-rMD6B55bzV2QwaywiyETeAsAnrqqm7',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuC1-nxbGqLKDJGtbcjqyydLskV9I_DldOWh9wVoAH59QyMYPqbHs-uHd56bpcNYmGq5_QD00ol-PkFwwE6S9j6n-LC-bW87x95jk72qG7Vt9VUTG9xncZ6FG-DArLAoGNsMV0CauC9tjjJGnYvHIw8nNZ8oYBdlO4Dod3TBQ6lqthdMPRF99HATRh8ABEfaOQD5GxGvUOavqIV-HPv_m31_s2hr-qa04bgItWbWfYGz7nHsvFceNacf3XO6bgJe0UwhRqhDr5TcA_VK',
    null,
    null,
    null,
    null,
  ];

  static const int _minRequiredPhotos = 2;

  void _addPhoto(int index) {
    // 실제 구현에서는 이미지 피커 연동 필요
    HapticFeedback.lightImpact();
    // 더미 동작: 사진 추가
    setState(() {
      _photos[index] = 'https://picsum.photos/400/600?random=$index';
    });
  }

  void _removePhoto(int index) {
    HapticFeedback.lightImpact();
    setState(() {
      _photos[index] = null;
      // 빈 슬롯 정리 (뒤쪽 사진을 앞으로 당기기 등) 로직은 선택 사항
      // 여기서는 단순히 해당 슬롯만 비움
    });
  }

  int get _photoCount => _photos.where((p) => p != null).length;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                // 헤더
                _Header(
                  currentStep: widget.currentStep,
                  totalSteps: widget.totalSteps,
                  onBack: widget.onBack,
                ),
                // 메인 콘텐츠
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(24, 8, 24, 120),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 타이틀
                        const _TitleSection(),
                        const SizedBox(height: 24),
                        // 사진 그리드
                        GridView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          gridDelegate:
                              const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 2,
                                childAspectRatio: 3 / 4,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                          itemCount: 6,
                          itemBuilder: (context, index) {
                            final photoUrl = _photos[index];
                            return _PhotoSlot(
                              index: index,
                              photoUrl: photoUrl,
                              onAdd: () => _addPhoto(index),
                              onRemove: () => _removePhoto(index),
                            );
                          },
                        ),
                        const SizedBox(height: 24),
                        // 안내 문구
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Icon(
                              Icons.info_outline_rounded,
                              color: _AppColors.primary,
                              size: 18,
                            ),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '본인이 나오지 않거나 불쾌감을 주는 사진은 통보 없이 삭제될 수 있습니다.',
                                style: TextStyle(
                                  fontFamily: 'Noto Sans KR',
                                  fontSize: 12,
                                  color: _AppColors.textSub,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            // 하단 버튼
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _BottomActionBar(
                photoCount: _photoCount,
                minRequired: _minRequiredPhotos,
                onNext: () {
                  if (_photoCount >= _minRequiredPhotos) {
                    HapticFeedback.mediumImpact();
                    if (widget.onNext != null) {
                      widget.onNext!.call(_photos.whereType<String>().toList());
                    } else {
                      Navigator.of(
                        context,
                      ).pushNamed(RouteNames.onboardingSelfIntro);
                    }
                  } else {
                    HapticFeedback.heavyImpact();
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final int currentStep;
  final int totalSteps;
  final VoidCallback? onBack;

  const _Header({
    required this.currentStep,
    required this.totalSteps,
    this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: _AppColors.backgroundLight.withValues(alpha: 0.8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            onPressed: () {
              HapticFeedback.lightImpact();
              if (onBack != null) {
                onBack!.call();
              } else {
                Navigator.of(context).pop();
              }
            },
            icon: const Icon(
              Icons.arrow_back_rounded,
              color: _AppColors.textMain,
              size: 24,
            ),
            style: IconButton.styleFrom(
              padding: const EdgeInsets.all(8),
              backgroundColor: Colors.transparent,
            ),
          ),
          // 커스텀 프로그레스 인디케이터
          Row(
            children: List.generate(totalSteps, (index) {
              final isCurrent = index == currentStep - 1;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: isCurrent ? 24 : 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: isCurrent ? _AppColors.primary : _AppColors.progressBg,
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
          const SizedBox(width: 40),
        ],
      ),
    );
  }
}

// =============================================================================
// 타이틀 섹션
// =============================================================================
class _TitleSection extends StatelessWidget {
  const _TitleSection();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        Text(
          '프로필 사진 등록',
          style: TextStyle(
            fontFamily: 'Plus Jakarta Sans',
            fontSize: 26,
            fontWeight: FontWeight.bold,
            color: _AppColors.textMain,
            height: 1.3,
            letterSpacing: -0.5,
          ),
        ),
        SizedBox(height: 8),
        Text(
          '매력을 보여줄 사진을 올려주세요',
          style: TextStyle(
            fontFamily: 'Noto Sans KR',
            fontSize: 14,
            color: _AppColors.textSub,
          ),
        ),
        SizedBox(height: 8),
        Text(
          '얼굴이 잘 나온 사진일수록 매칭 확률이 올라가요',
          style: TextStyle(
            fontFamily: 'Noto Sans KR',
            fontSize: 14,
            color: _AppColors.textSub,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 사진 슬롯
// =============================================================================
class _PhotoSlot extends StatelessWidget {
  final int index;
  final String? photoUrl;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const _PhotoSlot({
    required this.index,
    required this.photoUrl,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    if (photoUrl != null) {
      // 채워진 상태
      return GestureDetector(
        onTap: () {
          // 수정 로직 (여기서는 추가와 동일하게 처리하거나 별도 구현)
          onAdd();
        },
        child: Stack(
          children: [
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.black.withValues(alpha: 0.05)),
                image: DecorationImage(
                  image: NetworkImage(photoUrl!),
                  fit: BoxFit.cover,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
            ),
            // 대표 뱃지 (첫 번째 슬롯)
            if (index == 0)
              Positioned(
                top: 8,
                left: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _AppColors.primary,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.1),
                        blurRadius: 2,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                  child: const Text(
                    '대표',
                    style: TextStyle(
                      fontFamily: 'Noto Sans KR',
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            // 삭제 버튼
            Positioned(
              top: -8,
              right: -8,
              child: GestureDetector(
                onTap: onRemove,
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: _AppColors.surfaceLight,
                    shape: BoxShape.circle,
                    border: Border.all(color: _AppColors.backgroundLight),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.1),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.close_rounded,
                    size: 16,
                    color: _AppColors.textGray,
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    } else {
      // 빈 상태
      return GestureDetector(
        onTap: onAdd,
        child: Container(
          decoration: BoxDecoration(
            color: _AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: _AppColors.borderDashed,
              width: 2,
              style: BorderStyle
                  .none, // Dotted/Dashed는 CustomPainter 필요하나, 간단히 실선 혹은 구현 타협
            ),
          ),
          // Dashed Border 효과를 위해 CustomPaint를 사용할 수 있으나 복잡도 줄이기 위해 스타일링 대체
          child: CustomPaint(
            painter: _DashedBorderPainter(
              color: _AppColors.borderDashed,
              strokeWidth: 2,
              gap: 4,
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: _AppColors.backgroundLight,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.add_rounded,
                      color: _AppColors.textGray,
                      size: 24,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '추가',
                    style: TextStyle(
                      fontFamily: 'Noto Sans KR',
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _AppColors.textSub,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }
  }
}

// Dashed Border Painter
class _DashedBorderPainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  final double gap;

  _DashedBorderPainter({
    required this.color,
    this.strokeWidth = 2,
    this.gap = 4,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke;

    final Path path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(0, 0, size.width, size.height),
          const Radius.circular(16),
        ),
      );

    final Path dashPath = Path();
    final double dashWidth = 8.0;

    for (final PathMetric metric in path.computeMetrics()) {
      double distance = 0.0;
      while (distance < metric.length) {
        dashPath.addPath(
          metric.extractPath(distance, distance + dashWidth),
          Offset.zero,
        );
        distance += dashWidth + gap;
      }
    }

    canvas.drawPath(dashPath, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// =============================================================================
// 하단 액션바
// =============================================================================
class _BottomActionBar extends StatelessWidget {
  final int photoCount;
  final int minRequired;
  final VoidCallback onNext;

  const _BottomActionBar({
    required this.photoCount,
    required this.minRequired,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    final bool isEnabled = photoCount >= minRequired;

    return Container(
      padding: EdgeInsets.fromLTRB(
        24,
        16,
        24,
        MediaQuery.of(context).padding.bottom + 24,
      ),
      decoration: BoxDecoration(
        color: _AppColors.backgroundLight.withValues(alpha: 0.95),
        border: const Border(top: BorderSide(color: Colors.transparent)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '최소 $minRequired장 업로드를 권장해요',
            style: const TextStyle(
              fontFamily: 'Noto Sans KR',
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: _AppColors.textGray,
            ),
          ),
          const SizedBox(height: 12),
          CupertinoButton(
            padding: EdgeInsets.zero,
            onPressed: onNext,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              height: 56,
              decoration: BoxDecoration(
                color: isEnabled
                    ? _AppColors.primary
                    : _AppColors.primary.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(16),
                boxShadow: isEnabled
                    ? [
                        BoxShadow(
                          color: _AppColors.primary.withValues(alpha: 0.3),
                          blurRadius: 12,
                          offset: const Offset(0, 6),
                        ),
                      ]
                    : null,
              ),
              child: Center(
                child: Text(
                  '다음',
                  style: TextStyle(
                    fontFamily: 'Plus Jakarta Sans',
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white.withValues(
                      alpha: isEnabled ? 1.0 : 0.8,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
