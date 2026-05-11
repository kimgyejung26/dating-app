import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_3d_controller/flutter_3d_controller.dart';

const String stampModelAsset = 'assets/models/stamp_scene_animated.glb';

String stampModelSource({bool isWeb = kIsWeb}) {
  return isWeb ? 'assets/$stampModelAsset' : stampModelAsset;
}

String? selectStampAnimationName(List<String> animations) {
  if (animations.isEmpty) {
    return null;
  }

  if (animations.contains('Stamp')) {
    return 'Stamp';
  }

  for (final animation in animations) {
    if (animation.toLowerCase() == 'stamp') {
      return animation;
    }
  }

  for (final animation in animations) {
    if (animation.toLowerCase().contains('stamp')) {
      return animation;
    }
  }

  return animations.first;
}

class Real3DStampPage extends StatefulWidget {
  const Real3DStampPage({super.key, this.modelViewerBuilder});

  final WidgetBuilder? modelViewerBuilder;

  @override
  State<Real3DStampPage> createState() => _Real3DStampPageState();
}

class _Real3DStampPageState extends State<Real3DStampPage>
    with SingleTickerProviderStateMixin {
  static const Duration stampDuration = Duration(milliseconds: 1100);
  static const Duration impactTiming = Duration(milliseconds: 500);

  final Flutter3DController _modelController = Flutter3DController();

  late final AnimationController _impactController;

  bool _modelLoaded = false;
  bool _isPlaying = false;
  String? _stampAnimationName;
  double _loadingProgress = 0;
  String? _loadError;
  Timer? _impactTimer;
  Timer? _finishTimer;

  @override
  void initState() {
    super.initState();
    _impactController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 420),
    );
  }

  Future<void> _handleModelLoaded(String modelAddress) async {
    if (!mounted) {
      return;
    }

    setState(() {
      _modelLoaded = true;
      _loadError = null;
      _loadingProgress = 1;
    });

    try {
      final animations = await _modelController.getAvailableAnimations();
      debugPrint('stamp_scene_animated.glb animations: $animations');

      if (!mounted) {
        return;
      }

      setState(() {
        _stampAnimationName = selectStampAnimationName(animations);
      });

      _modelController.setCameraTarget(0, 0, 0);
      _modelController.setCameraOrbit(0, 0, 180);
    } catch (error, stackTrace) {
      debugPrint('Failed to prepare 3D stamp model: $error');
      debugPrintStack(stackTrace: stackTrace);

      if (!mounted) {
        return;
      }

      setState(() {
        _loadError = '3D 모델은 로드됐지만 애니메이션 정보를 읽지 못했습니다.';
      });
    }
  }

  void _handleProgress(double progress) {
    if (!mounted) {
      return;
    }

    setState(() {
      _loadingProgress = progress.clamp(0.0, 1.0).toDouble();
    });
  }

  void _handleError(String error) {
    if (!mounted) {
      return;
    }

    setState(() {
      _modelLoaded = false;
      _isPlaying = false;
      _loadError = error;
    });
  }

  Future<void> _playStamp() async {
    if (!_modelLoaded || _isPlaying) {
      return;
    }

    _impactTimer?.cancel();
    _finishTimer?.cancel();

    setState(() {
      _isPlaying = true;
    });

    try {
      _modelController.stopAnimation();
      await Future<void>.delayed(const Duration(milliseconds: 40));
      _modelController.resetAnimation();
      await Future<void>.delayed(const Duration(milliseconds: 16));

      _modelController.playAnimation(
        animationName: _stampAnimationName,
        loopCount: 1,
      );

      _impactTimer = Timer(impactTiming, _playImpactEffect);
      _finishTimer = Timer(stampDuration, _finishPlayback);
    } catch (error, stackTrace) {
      debugPrint('Failed to play 3D stamp animation: $error');
      debugPrintStack(stackTrace: stackTrace);

      if (!mounted) {
        return;
      }

      setState(() {
        _isPlaying = false;
        _loadError = '도장 애니메이션을 재생하지 못했습니다.';
      });
    }
  }

  void _playImpactEffect() {
    HapticFeedback.mediumImpact();
    _impactController.forward(from: 0);
  }

  void _finishPlayback() {
    if (!mounted) {
      return;
    }

    _modelController.pauseAnimation();

    setState(() {
      _isPlaying = false;
    });
  }

  @override
  void dispose() {
    _impactTimer?.cancel();
    _finishTimer?.cancel();
    _impactController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final buttonText = _buttonText;
    final canStamp = _modelLoaded && !_isPlaying && _loadError == null;

    return Scaffold(
      backgroundColor: const Color(0xfff4efe3),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Expanded(
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: const Color(0xfffffbf2),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: const [
                              BoxShadow(
                                blurRadius: 26,
                                offset: Offset(0, 14),
                                color: Color(0x1f000000),
                              ),
                            ],
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child:
                                widget.modelViewerBuilder?.call(context) ??
                                Flutter3DViewer(
                                  src: stampModelSource(),
                                  controller: _modelController,
                                  enableTouch: false,
                                  activeGestureInterceptor: true,
                                  progressBarColor: const Color(0xffb21f2d),
                                  onLoad: (modelAddress) {
                                    unawaited(_handleModelLoaded(modelAddress));
                                  },
                                  onProgress: _handleProgress,
                                  onError: _handleError,
                                ),
                          ),
                        ),
                        if (!_modelLoaded || _loadError != null)
                          Positioned.fill(
                            child: _ModelStatusOverlay(
                              progress: _loadingProgress,
                              error: _loadError,
                            ),
                          ),
                        IgnorePointer(
                          child: _ImpactPulse(controller: _impactController),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 22),
                  SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: FilledButton(
                      onPressed: canStamp ? _playStamp : null,
                      child: Text(
                        buttonText,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  String get _buttonText {
    if (_isPlaying) {
      return '찍는 중...';
    }

    if (_loadError != null) {
      return '모델 확인 필요';
    }

    if (!_modelLoaded) {
      return '3D 모델 로딩 중...';
    }

    return '도장 찍기';
  }
}

class _ModelStatusOverlay extends StatelessWidget {
  const _ModelStatusOverlay({required this.progress, required this.error});

  final double progress;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final hasError = error != null;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xfffffbf2).withValues(alpha: 0.92),
      ),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (hasError)
                const Icon(
                  Icons.view_in_ar_outlined,
                  color: Color(0xff9a1f2b),
                  size: 40,
                )
              else
                SizedBox(
                  width: 42,
                  height: 42,
                  child: CircularProgressIndicator(
                    value: progress > 0 && progress < 1 ? progress : null,
                    color: const Color(0xffb21f2d),
                  ),
                ),
              const SizedBox(height: 18),
              Text(
                hasError ? '3D 모델을 불러오지 못했습니다.' : '3D 모델 로딩 중...',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                hasError
                    ? 'assets/models/stamp_scene_animated.glb 파일이 있는지, pubspec.yaml에 asset이 등록됐는지 확인해주세요.'
                    : '${(progress * 100).clamp(0, 100).round()}%',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xff665f55),
                  fontSize: 14,
                  height: 1.45,
                ),
              ),
              if (hasError) ...[
                const SizedBox(height: 8),
                Text(
                  error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xff8c8173),
                    fontSize: 12,
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

class _ImpactPulse extends StatelessWidget {
  const _ImpactPulse({required this.controller});

  final AnimationController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        final value = Curves.easeOutCubic.transform(controller.value);
        final opacity = (1 - value).clamp(0.0, 1.0).toDouble();

        return Transform.scale(
          scale: 0.62 + value * 0.58,
          child: Opacity(
            opacity: opacity,
            child: Container(
              width: 210,
              height: 210,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: const Color(0xffb21f2d).withValues(alpha: 0.34),
                  width: 5,
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
