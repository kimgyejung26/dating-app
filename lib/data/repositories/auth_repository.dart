/// 인증 리포지토리
abstract class AuthRepository {
  /// 카카오 로그인
  Future<AuthResult> loginWithKakao(String kakaoAccessToken);

  /// 토큰 갱신
  Future<AuthResult> refreshToken(String refreshToken);

  /// 로그아웃
  Future<void> logout();

  /// 회원탈퇴
  Future<void> withdraw();

  /// 현재 로그인 상태 확인
  Future<bool> isLoggedIn();
}

/// 인증 결과
class AuthResult {
  final String accessToken;
  final String refreshToken;
  final bool isNewUser;

  const AuthResult({
    required this.accessToken,
    required this.refreshToken,
    required this.isNewUser,
  });
}
