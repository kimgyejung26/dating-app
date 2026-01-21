import 'package:cloud_firestore/cloud_firestore.dart';

class UserService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

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

  Future<Map<String, dynamic>?> getUserProfile(String kakaoUserId) async {
    final doc = await _firestore.collection('users').doc(kakaoUserId).get();
    return doc.data();
  }
}
