import '../models/event/group_match_model.dart';

/// 이벤트 리포지토리
abstract class EventRepository {
  /// 3:3 매칭 생성
  Future<GroupMatchModel> createGroupMatch();

  /// 3:3 매칭 참가
  Future<GroupMatchModel> joinGroupMatch(String matchId);

  /// 3:3 매칭 상태 조회
  Future<GroupMatchModel> getGroupMatchStatus(String matchId);

  /// 3:3 매칭 취소
  Future<void> cancelGroupMatch(String matchId);

  /// 슬롯머신 돌리기
  Future<SlotMachineResult> spinSlotMachine();

  /// 제휴 목록 조회
  Future<List<Partnership>> getPartnerships();
}

/// 슬롯머신 결과
class SlotMachineResult {
  final bool isWin;
  final String? prizeType;
  final int? prizeAmount;

  const SlotMachineResult({
    required this.isWin,
    this.prizeType,
    this.prizeAmount,
  });
}

/// 제휴 정보
class Partnership {
  final String id;
  final String name;
  final String description;
  final String imageUrl;
  final String? couponCode;

  const Partnership({
    required this.id,
    required this.name,
    required this.description,
    required this.imageUrl,
    this.couponCode,
  });
}
