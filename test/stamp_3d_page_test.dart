import 'package:flutter_test/flutter_test.dart';
import 'package:stamp_animation/features/stamp_3d/real_3d_stamp_page.dart';

void main() {
  group('selectStampAnimationName', () {
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
}
