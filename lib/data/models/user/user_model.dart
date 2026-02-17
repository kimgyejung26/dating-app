/// 사용자 모델
class UserModel {
  final String id;
  final String nickname;
  final String? profileImageUrl;
  final int age;
  final String gender;
  final String? department;
  final String? university;
  final int? height;
  final String? mbti;
  final List<String> interests;
  final String? introduction;
  final DateTime createdAt;
  final DateTime updatedAt;

  const UserModel({
    required this.id,
    required this.nickname,
    this.profileImageUrl,
    required this.age,
    required this.gender,
    this.department,
    this.university,
    this.height,
    this.mbti,
    this.interests = const [],
    this.introduction,
    required this.createdAt,
    required this.updatedAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as String,
      nickname: json['nickname'] as String,
      profileImageUrl: json['profileImageUrl'] as String?,
      age: json['age'] as int,
      gender: json['gender'] as String,
      department: json['department'] as String?,
      university: json['university'] as String?,
      height: json['height'] as int?,
      mbti: json['mbti'] as String?,
      interests:
          (json['interests'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      introduction: json['introduction'] as String?,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nickname': nickname,
      'profileImageUrl': profileImageUrl,
      'age': age,
      'gender': gender,
      'department': department,
      'university': university,
      'height': height,
      'mbti': mbti,
      'interests': interests,
      'introduction': introduction,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }

  UserModel copyWith({
    String? id,
    String? nickname,
    String? profileImageUrl,
    int? age,
    String? gender,
    String? department,
    String? university,
    int? height,
    String? mbti,
    List<String>? interests,
    String? introduction,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return UserModel(
      id: id ?? this.id,
      nickname: nickname ?? this.nickname,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      age: age ?? this.age,
      gender: gender ?? this.gender,
      department: department ?? this.department,
      university: university ?? this.university,
      height: height ?? this.height,
      mbti: mbti ?? this.mbti,
      interests: interests ?? this.interests,
      introduction: introduction ?? this.introduction,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
