import '../models/matching/match_model.dart';

/// 매칭 리포지토리
abstract class MatchingRepository {
  /// 매칭 카드 목록 조회
  Future<List<MatchModel>> getMatchingCards({int limit = 10});

  /// 좋아요 (하트 보내기)
  Future<MatchResult> like(String matchId);

  /// 패스 (넘기기)
  Future<void> pass(String matchId);

  /// 슈퍼 좋아요
  Future<MatchResult> superLike(String matchId);

  /// 매칭 취소
  Future<void> cancelMatch(String matchId);

  /// AI 취향 분석 결과 조회
  Future<AiPreferenceAnalysis> getAiAnalysis();
}

/// 매칭 결과
class MatchResult {
  final bool isMatched;
  final String? chatRoomId;

  const MatchResult({required this.isMatched, this.chatRoomId});
}

/// AI 취향 분석
class AiPreferenceAnalysis {
  final List<String> topKeywords;
  final Map<String, double> categoryScores;
  final String summary;

  const AiPreferenceAnalysis({
    required this.topKeywords,
    required this.categoryScores,
    required this.summary,
  });
}
