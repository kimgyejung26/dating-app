class PreferenceModel {
  final String? preferredGender;
  final String? preferredMbti;
  final String? preferredAttachmentType;
  final String? preferredMajorCategory;
  final int? minAge;
  final int? maxAge;
  final int? minHeight;
  final int? maxHeight;
  final List<String>? preferredInterests;
  final Map<String, dynamic>? lifestylePreferences;

  PreferenceModel({
    this.preferredGender,
    this.preferredMbti,
    this.preferredAttachmentType,
    this.preferredMajorCategory,
    this.minAge,
    this.maxAge,
    this.minHeight,
    this.maxHeight,
    this.preferredInterests,
    this.lifestylePreferences,
  });

  factory PreferenceModel.fromJson(Map<String, dynamic> json) {
    return PreferenceModel(
      preferredGender: json['preferredGender'] as String?,
      preferredMbti: json['preferredMbti'] as String?,
      preferredAttachmentType: json['preferredAttachmentType'] as String?,
      preferredMajorCategory: json['preferredMajorCategory'] as String?,
      minAge: json['minAge'] as int?,
      maxAge: json['maxAge'] as int?,
      minHeight: json['minHeight'] as int?,
      maxHeight: json['maxHeight'] as int?,
      preferredInterests: json['preferredInterests'] != null
          ? List<String>.from(json['preferredInterests'] as List)
          : null,
      lifestylePreferences:
          json['lifestylePreferences'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'preferredGender': preferredGender,
      'preferredMbti': preferredMbti,
      'preferredAttachmentType': preferredAttachmentType,
      'preferredMajorCategory': preferredMajorCategory,
      'minAge': minAge,
      'maxAge': maxAge,
      'minHeight': minHeight,
      'maxHeight': maxHeight,
      'preferredInterests': preferredInterests,
      'lifestylePreferences': lifestylePreferences,
    };
  }
}
