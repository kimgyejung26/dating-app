class Validators {
  // Phone Number Validation (Korean format)
  static bool isValidPhoneNumber(String? phone) {
    if (phone == null || phone.isEmpty) return false;
    final regex = RegExp(r'^010-\d{4}-\d{4}$|^010\d{8}$');
    return regex.hasMatch(phone.replaceAll(RegExp(r'[\s-]'), ''));
  }

  // Email Validation
  static bool isValidEmail(String? email) {
    if (email == null || email.isEmpty) return false;
    final regex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    return regex.hasMatch(email);
  }

  // Verification Code Validation (6 digits)
  static bool isValidVerificationCode(String? code) {
    if (code == null || code.isEmpty) return false;
    final regex = RegExp(r'^\d{6}$');
    return regex.hasMatch(code);
  }

  // Nickname Validation (2-10 characters)
  static bool isValidNickname(String? nickname) {
    if (nickname == null || nickname.isEmpty) return false;
    return nickname.length >= 2 && nickname.length <= 10;
  }

  // Age Validation
  static bool isValidAge(int? age) {
    if (age == null) return false;
    return age >= 18 && age <= 100;
  }

  // Height Validation (cm)
  static bool isValidHeight(int? height) {
    if (height == null) return false;
    return height >= 100 && height <= 250;
  }
}
