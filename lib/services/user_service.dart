import 'package:cloud_firestore/cloud_firestore.dart';

class UserService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // ---------------------------------------------------------------------------
  // 카카오 유저 생성/갱신
  // ---------------------------------------------------------------------------

  Future<void> upsertKakaoUser({
    required String kakaoUserId,
    required String? nickname,
    required String? profileImageUrl,
    String? email,
    Map<String, dynamic>? extraFields,
  }) async {
    final docRef = _firestore.collection('users').doc(kakaoUserId);
    final now = FieldValue.serverTimestamp();

    final snapshot = await docRef.get();
    if (!snapshot.exists) {
      final data = {
        'kakaoUserId': kakaoUserId,
        'nickname': nickname,
        'profileImageUrl': profileImageUrl,
        'email': email,
        'createdAt': now,
        'lastLoginAt': now,
      };
      if (extraFields != null) {
        data.addAll(extraFields);
      }
      await docRef.set(data);
      return;
    }

    final updateData = {
      'nickname': nickname,
      'profileImageUrl': profileImageUrl,
      'email': email,
      'lastLoginAt': now,
    };
    if (extraFields != null) {
      updateData.addAll(extraFields);
    }
    await docRef.update(updateData);
  }

  Future<bool> existsKakaoUser(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    return doc.exists;
  }

  // ---------------------------------------------------------------------------
  // 온보딩 상태
  // ---------------------------------------------------------------------------

  Future<bool> isInitialSetupComplete(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    if (!doc.exists) return false;
    final data = doc.data();
    return data?['initialSetupComplete'] == true;
  }

  Future<bool> hasSeenTutorial(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    if (!doc.exists) return false;
    final data = doc.data();
    return data?['hasSeenTutorial'] == true;
  }

  Future<void> setTutorialSeen(String kakaoUserId) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'hasSeenTutorial': true,
    }, SetOptions(merge: true));
  }

  // ---------------------------------------------------------------------------
  // 프로필 조회
  // ---------------------------------------------------------------------------

  Future<Map<String, dynamic>?> getUserProfile(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    return doc.data();
  }

  // ---------------------------------------------------------------------------
  // 학생 인증
  // ---------------------------------------------------------------------------

  Future<bool> isStudentVerified(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    if (!doc.exists) return false;
    final data = doc.data();
    return data?['isStudentVerified'] == true;
  }

  Future<String?> getStudentEmail(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    if (!doc.exists) return null;
    final data = doc.data();
    return data?['studentEmail']?.toString();
  }

  Future<void> setStudentVerification({
    required String kakaoUserId,
    required String studentEmail,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'studentEmail': studentEmail,
      'isStudentVerified': true,
      'studentVerifiedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  // ---------------------------------------------------------------------------
  // 온보딩 정보 저장 (단계별 merge)
  // ---------------------------------------------------------------------------

  /// 온보딩 기본 정보 (성별, 나이, 키, MBTI, 대학, 학과 등)
  Future<void> saveOnboardingBasicInfo({
    required String kakaoUserId,
    required Map<String, dynamic> basicInfo,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'onboarding': basicInfo,
      'onboardingUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 온보딩 사진 URL 저장
  Future<void> saveOnboardingPhotos({
    required String kakaoUserId,
    required List<String> photoUrls,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'onboarding': {'photoUrls': photoUrls},
      'onboardingUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 온보딩 키워드/관심사 저장
  Future<void> saveOnboardingKeywords({
    required String kakaoUserId,
    required List<String> keywords,
    required List<String> interests,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'onboarding': {
        'keywords': keywords,
        'interests': interests,
      },
      'onboardingUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 온보딩 프로필 문답 저장
  Future<void> saveOnboardingProfileQa({
    required String kakaoUserId,
    required List<Map<String, String>> profileQa,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'onboarding': {'profileQa': profileQa},
      'onboardingUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 온보딩 완료 플래그
  Future<void> completeOnboarding(String kakaoUserId) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'initialSetupComplete': true,
      'onboardingCompletedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  // ---------------------------------------------------------------------------
  // 이상형 정보 저장
  // ---------------------------------------------------------------------------

  /// 이상형 전체 저장 (한 번에 또는 마지막 단계 완료 시)
  Future<void> saveIdealType({
    required String kakaoUserId,
    required Map<String, dynamic> idealType,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'idealType': idealType,
      'idealTypeUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 이상형 부분 업데이트 (키, 나이, MBTI, 학과, 성격, 라이프스타일 각각)
  Future<void> updateIdealTypeField({
    required String kakaoUserId,
    required String fieldName,
    required dynamic value,
  }) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'idealType': {fieldName: value},
      'idealTypeUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 이상형 설정 건너뛰기
  Future<void> skipIdealType(String kakaoUserId) async {
    await _firestore.collection('users').doc(kakaoUserId).set({
      'idealType': {'skipped': true},
      'idealTypeUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  /// 이상형 정보 조회
  Future<Map<String, dynamic>?> getIdealType(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    if (!doc.exists) return null;
    return doc.data()?['idealType'] as Map<String, dynamic>?;
  }
}
