/// 포맷팅 유틸리티
class Formatters {
  Formatters._();

  /// 전화번호 포맷팅 (010-1234-5678)
  static String formatPhoneNumber(String phone) {
    final cleaned = phone.replaceAll(RegExp(r'\D'), '');
    if (cleaned.length == 11) {
      return '${cleaned.substring(0, 3)}-${cleaned.substring(3, 7)}-${cleaned.substring(7)}';
    }
    return phone;
  }

  /// 날짜 포맷팅
  static String formatDate(DateTime date, {String pattern = 'yyyy.MM.dd'}) {
    // 간단한 형식 지원
    return '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
  }

  /// 상대 시간 포맷팅 (방금, 5분 전, 1시간 전 등)
  static String formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inSeconds < 60) {
      return '방금';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}분 전';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}시간 전';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}일 전';
    } else {
      return formatDate(dateTime);
    }
  }

  /// 숫자 천단위 콤마 포맷팅
  static String formatNumber(int number) {
    if (number < 1000) return number.toString();
    final str = number.toString();
    final buffer = StringBuffer();
    for (int i = 0; i < str.length; i++) {
      if (i > 0 && (str.length - i) % 3 == 0) {
        buffer.write(',');
      }
      buffer.write(str[i]);
    }
    return buffer.toString();
  }

  /// 키 포맷팅 (178cm)
  static String formatHeight(int height) {
    return '${height}cm';
  }

  /// 나이 포맷팅 (25세)
  static String formatAge(int age) {
    return '$age세';
  }
}
