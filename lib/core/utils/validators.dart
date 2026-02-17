/// 입력 유효성 검사 유틸리티
class Validators {
  Validators._();

  /// 이메일 유효성 검사
  static bool isValidEmail(String email) {
    final regex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    return regex.hasMatch(email);
  }

  /// 전화번호 유효성 검사 (한국)
  static bool isValidPhoneNumber(String phone) {
    final regex = RegExp(r'^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$');
    return regex.hasMatch(phone.replaceAll('-', ''));
  }

  /// 닉네임 유효성 검사 (2-10자, 한글/영문/숫자)
  static bool isValidNickname(String nickname) {
    if (nickname.length < 2 || nickname.length > 10) return false;
    final regex = RegExp(r'^[가-힣a-zA-Z0-9]+$');
    return regex.hasMatch(nickname);
  }

  /// 자기소개 유효성 검사 (최소 10자)
  static bool isValidIntroduction(String intro) {
    return intro.trim().length >= 10;
  }

  /// 키 유효성 검사 (140-220cm)
  static bool isValidHeight(int height) {
    return height >= 140 && height <= 220;
  }

  /// 나이 유효성 검사 (19-99세)
  static bool isValidAge(int age) {
    return age >= 19 && age <= 99;
  }
}
