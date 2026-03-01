import 'package:flutter/cupertino.dart';

/// Flutter 확장 함수 모음
extension StringExtensions on String {
  /// 첫 글자만 대문자로 변환
  String capitalize() {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }

  /// 빈 문자열 또는 공백만 있는지 확인
  bool get isBlank => trim().isEmpty;

  /// 유효한 문자열인지 확인
  bool get isNotBlank => !isBlank;
}

extension DateTimeExtensions on DateTime {
  /// 오늘인지 확인
  bool get isToday {
    final now = DateTime.now();
    return year == now.year && month == now.month && day == now.day;
  }

  /// 어제인지 확인
  bool get isYesterday {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    return year == yesterday.year &&
        month == yesterday.month &&
        day == yesterday.day;
  }

  /// 나이 계산
  int get age {
    final now = DateTime.now();
    int age = now.year - year;
    if (now.month < month || (now.month == month && now.day < day)) {
      age--;
    }
    return age;
  }
}

extension ContextExtensions on BuildContext {
  /// 화면 너비
  double get screenWidth => MediaQuery.of(this).size.width;

  /// 화면 높이
  double get screenHeight => MediaQuery.of(this).size.height;

  /// Safe Area 패딩
  EdgeInsets get safeAreaPadding => MediaQuery.of(this).padding;

  /// 키보드가 열려있는지 확인
  bool get isKeyboardOpen => MediaQuery.of(this).viewInsets.bottom > 0;
}

extension ListExtensions<T> on List<T> {
  /// 안전하게 인덱스로 접근 (범위 초과 시 null 반환)
  T? getOrNull(int index) {
    if (index < 0 || index >= length) return null;
    return this[index];
  }
}
