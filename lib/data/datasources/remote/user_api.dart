import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';

/// 사용자 API 데이터소스
class UserApi {
  final ApiClient _client;

  UserApi(this._client);

  /// 현재 사용자 조회
  Future<Map<String, dynamic>> getCurrentUser() async {
    return await _client.get(ApiEndpoints.userProfile);
  }

  /// 프로필 업데이트
  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    return await _client.put(ApiEndpoints.userUpdate, body: data);
  }
}
