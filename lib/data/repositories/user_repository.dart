import '../models/user/user_model.dart';
import '../models/user/user_profile_model.dart';

/// 사용자 리포지토리
abstract class UserRepository {
  /// 현재 사용자 정보 조회
  Future<UserModel> getCurrentUser();

  /// 사용자 프로필 조회
  Future<UserProfileModel> getUserProfile(String userId);

  /// 프로필 업데이트
  Future<UserModel> updateProfile({
    String? nickname,
    String? introduction,
    int? height,
    String? mbti,
    List<String>? interests,
  });

  /// 프로필 사진 업로드
  Future<String> uploadProfilePhoto(String filePath);

  /// 프로필 사진 삭제
  Future<void> deleteProfilePhoto(String photoUrl);

  /// 프로필 사진 순서 변경
  Future<List<String>> reorderPhotos(List<String> photoUrls);

  /// 이상형 설정 업데이트
  Future<void> updateIdealType(IdealTypePreferences preferences);
}
