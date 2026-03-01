class UserModel {
  final String id;
  final String? username;
  final String? nickname;
  final String? email;
  final String? phoneNumber;
  final String? gender;
  final String? bio;
  final List<String>? photos;
  final String? mbti;
  final String? attachmentType;
  final String? majorCategory;
  final List<String>? interests;
  final Map<String, dynamic>? lifestyle;
  final bool isStudentVerified;
  final bool isInitialSetupComplete;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  UserModel({
    required this.id,
    this.username,
    this.nickname,
    this.email,
    this.phoneNumber,
    this.gender,
    this.bio,
    this.photos,
    this.mbti,
    this.attachmentType,
    this.majorCategory,
    this.interests,
    this.lifestyle,
    this.isStudentVerified = false,
    this.isInitialSetupComplete = false,
    this.createdAt,
    this.updatedAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as String,
      username: json['username'] as String?,
      nickname: json['nickname'] as String?,
      email: json['email'] as String?,
      phoneNumber: json['phoneNumber'] as String?,
      gender: json['gender'] as String?,
      bio: json['bio'] as String?,
      photos: json['photos'] != null
          ? List<String>.from(json['photos'] as List)
          : null,
      mbti: json['mbti'] as String?,
      attachmentType: json['attachmentType'] as String?,
      majorCategory: json['majorCategory'] as String?,
      interests: json['interests'] != null
          ? List<String>.from(json['interests'] as List)
          : null,
      lifestyle: json['lifestyle'] as Map<String, dynamic>?,
      isStudentVerified: json['isStudentVerified'] as bool? ?? false,
      isInitialSetupComplete: json['isInitialSetupComplete'] as bool? ?? false,
      createdAt: json['createdAt'] != null
          ? DateTime.parse(json['createdAt'] as String)
          : null,
      updatedAt: json['updatedAt'] != null
          ? DateTime.parse(json['updatedAt'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'nickname': nickname,
      'email': email,
      'phoneNumber': phoneNumber,
      'gender': gender,
      'bio': bio,
      'photos': photos,
      'mbti': mbti,
      'attachmentType': attachmentType,
      'majorCategory': majorCategory,
      'interests': interests,
      'lifestyle': lifestyle,
      'isStudentVerified': isStudentVerified,
      'isInitialSetupComplete': isInitialSetupComplete,
      'createdAt': createdAt?.toIso8601String(),
      'updatedAt': updatedAt?.toIso8601String(),
    };
  }

  UserModel copyWith({
    String? id,
    String? username,
    String? nickname,
    String? email,
    String? phoneNumber,
    String? gender,
    String? bio,
    List<String>? photos,
    String? mbti,
    String? attachmentType,
    String? majorCategory,
    List<String>? interests,
    Map<String, dynamic>? lifestyle,
    bool? isStudentVerified,
    bool? isInitialSetupComplete,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return UserModel(
      id: id ?? this.id,
      username: username ?? this.username,
      nickname: nickname ?? this.nickname,
      email: email ?? this.email,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      gender: gender ?? this.gender,
      bio: bio ?? this.bio,
      photos: photos ?? this.photos,
      mbti: mbti ?? this.mbti,
      attachmentType: attachmentType ?? this.attachmentType,
      majorCategory: majorCategory ?? this.majorCategory,
      interests: interests ?? this.interests,
      lifestyle: lifestyle ?? this.lifestyle,
      isStudentVerified: isStudentVerified ?? this.isStudentVerified,
      isInitialSetupComplete:
          isInitialSetupComplete ?? this.isInitialSetupComplete,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
