/// 3:3 그룹 매칭 모델
class GroupMatchModel {
  final String id;
  final String status; // 'waiting' | 'matching' | 'matched' | 'cancelled'
  final GroupInfo myGroup;
  final GroupInfo? matchedGroup;
  final DateTime? matchedAt;
  final DateTime createdAt;

  const GroupMatchModel({
    required this.id,
    required this.status,
    required this.myGroup,
    this.matchedGroup,
    this.matchedAt,
    required this.createdAt,
  });

  factory GroupMatchModel.fromJson(Map<String, dynamic> json) {
    return GroupMatchModel(
      id: json['id'] as String,
      status: json['status'] as String,
      myGroup: GroupInfo.fromJson(json['myGroup'] as Map<String, dynamic>),
      matchedGroup: json['matchedGroup'] != null
          ? GroupInfo.fromJson(json['matchedGroup'] as Map<String, dynamic>)
          : null,
      matchedAt: json['matchedAt'] != null
          ? DateTime.parse(json['matchedAt'] as String)
          : null,
      createdAt: DateTime.parse(json['createdAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'status': status,
      'myGroup': myGroup.toJson(),
      'matchedGroup': matchedGroup?.toJson(),
      'matchedAt': matchedAt?.toIso8601String(),
      'createdAt': createdAt.toIso8601String(),
    };
  }
}

/// 그룹 정보
class GroupInfo {
  final String id;
  final List<GroupMember> members;
  final bool isReady;

  const GroupInfo({
    required this.id,
    this.members = const [],
    this.isReady = false,
  });

  factory GroupInfo.fromJson(Map<String, dynamic> json) {
    return GroupInfo(
      id: json['id'] as String,
      members:
          (json['members'] as List<dynamic>?)
              ?.map((e) => GroupMember.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      isReady: json['isReady'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'members': members.map((e) => e.toJson()).toList(),
      'isReady': isReady,
    };
  }
}

/// 그룹 멤버
class GroupMember {
  final String id;
  final String nickname;
  final String? profileImageUrl;
  final bool isLeader;

  const GroupMember({
    required this.id,
    required this.nickname,
    this.profileImageUrl,
    this.isLeader = false,
  });

  factory GroupMember.fromJson(Map<String, dynamic> json) {
    return GroupMember(
      id: json['id'] as String,
      nickname: json['nickname'] as String,
      profileImageUrl: json['profileImageUrl'] as String?,
      isLeader: json['isLeader'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nickname': nickname,
      'profileImageUrl': profileImageUrl,
      'isLeader': isLeader,
    };
  }
}
