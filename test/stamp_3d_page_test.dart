import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:stamp_animation/features/stamp_3d/real_3d_stamp_page.dart';

void main() {
  group('selectStampAnimationName', () {
    test('uses Flutter web asset URL when model-viewer runs on web', () {
      expect(
        stampModelSource(isWeb: true),
        'assets/assets/models/stamp_scene_animated.glb',
      );
      expect(
        stampModelSource(isWeb: false),
        'assets/models/stamp_scene_animated.glb',
      );
    });

    test('prefers exact Stamp match case-insensitively', () {
      expect(selectStampAnimationName(['Idle', 'stamp', 'Stamp']), 'Stamp');
    });

    test('falls back to the first animation containing stamp', () {
      expect(
        selectStampAnimationName(['Idle', 'QuickStampDown']),
        'QuickStampDown',
      );
    });

    test('falls back to the first animation when no stamp name exists', () {
      expect(selectStampAnimationName(['Idle', 'Bounce']), 'Idle');
    });

    test('returns null when the model has no animations', () {
      expect(selectStampAnimationName([]), isNull);
    });
  });

  group('stamp playback persistence', () {
    test('freezes before the model-viewer one-shot animation can reset', () {
      final source = File(
        'lib/features/stamp_3d/real_3d_stamp_page.dart',
      ).readAsStringSync();

      expect(
        source,
        contains(
          'static const Duration stampDuration = Duration(milliseconds: 1100);',
        ),
      );
    });

    test('pauses on finish so the 3D InkDecal final frame remains visible', () {
      final source = File(
        'lib/features/stamp_3d/real_3d_stamp_page.dart',
      ).readAsStringSync();
      final finishPlaybackBody =
          RegExp(
            r'void _finishPlayback\(\) \{([\s\S]*?)\n  \}',
          ).firstMatch(source)?.group(1) ??
          '';

      expect(
        finishPlaybackBody,
        contains('_modelController.pauseAnimation();'),
      );
    });
  });
}
