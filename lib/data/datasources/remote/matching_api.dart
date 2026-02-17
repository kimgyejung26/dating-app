import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';

/// 매칭 API 데이터소스
class MatchingApi {
  final ApiClient _client;

  MatchingApi(this._client);

  /// 매칭 카드 목록 조회
  Future<Map<String, dynamic>> getMatchingCards({int limit = 10}) async {
    return await _client.get('${ApiEndpoints.matchingCards}?limit=$limit');
  }

  /// 좋아요
  Future<Map<String, dynamic>> like(String matchId) async {
    return await _client.post(
      ApiEndpoints.matchingLike,
      body: {'matchId': matchId},
    );
  }

  /// 패스
  Future<void> pass(String matchId) async {
    await _client.post(ApiEndpoints.matchingPass, body: {'matchId': matchId});
  }
}
