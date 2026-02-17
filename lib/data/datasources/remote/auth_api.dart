import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';

/// 인증 API 데이터소스
class AuthApi {
  final ApiClient _client;

  AuthApi(this._client);

  /// 카카오 로그인
  Future<Map<String, dynamic>> loginWithKakao(String kakaoAccessToken) async {
    return await _client.post(
      ApiEndpoints.authKakao,
      body: {'kakaoAccessToken': kakaoAccessToken},
    );
  }

  /// 토큰 갱신
  Future<Map<String, dynamic>> refreshToken(String refreshToken) async {
    return await _client.post(
      ApiEndpoints.authRefresh,
      body: {'refreshToken': refreshToken},
    );
  }

  /// 로그아웃
  Future<void> logout() async {
    await _client.post(ApiEndpoints.authLogout);
  }
}
