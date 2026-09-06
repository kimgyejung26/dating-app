import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'app_check_readiness.dart';
import 'firebase_runtime.dart';
import 'storage_service.dart';

class PlayReviewSession {
  const PlayReviewSession({
    required this.reviewerUid,
    required this.blindMeetingId,
  });

  final String reviewerUid;
  final String blindMeetingId;
}

/// Dedicated Google Play reviewer authentication.
///
/// The ID/password are sent only to the App Check-protected callable. The app
/// never stores either credential and the returned Firebase account has no
/// email or phone identity attached to it.
class PlayReviewAccessService {
  PlayReviewAccessService({
    FirebaseAuth? firebaseAuth,
    FirebaseFunctions? functions,
    AppCheckReadiness? appCheckReadiness,
    StorageService? storageService,
  }) : _firebaseAuth = firebaseAuth ?? FirebaseAuth.instance,
       _functions =
           functions ??
           FirebaseFunctions.instanceFor(region: firebaseFunctionsRegion),
       _appCheckReadiness = appCheckReadiness ?? AppCheckReadiness.firebase(),
       _storageService = storageService ?? StorageService();

  static const reviewerUid = 'play-reviewer-v1';
  static const dataPartition = 'play_review';

  final FirebaseAuth _firebaseAuth;
  final FirebaseFunctions _functions;
  final AppCheckReadiness _appCheckReadiness;
  final StorageService _storageService;

  Future<PlayReviewSession> signIn({
    required String loginId,
    required String password,
  }) async {
    final normalizedId = loginId.trim();
    if (normalizedId.isEmpty || password.isEmpty) {
      throw StateError('review_credentials_required');
    }

    final appCheck = await _appCheckReadiness.preflight();
    if (!appCheck.isReady) throw StateError('app_check_unavailable');

    final response = await _functions.httpsCallable('playReviewSignIn').call({
      'loginId': normalizedId,
      'password': password,
    });
    final data = _asMap(response.data);
    final token = data['customToken']?.toString().trim() ?? '';
    final expectedUid = data['reviewerUid']?.toString().trim() ?? '';
    if (token.isEmpty || expectedUid != reviewerUid) {
      throw StateError('review_sign_in_response_invalid');
    }

    try {
      await _firebaseAuth.signInWithCustomToken(token);
      final user = _firebaseAuth.currentUser;
      final claims = (await user?.getIdTokenResult(true))?.claims;
      if (user?.uid != reviewerUid ||
          claims?['appSession'] != true ||
          claims?['playReviewer'] != true ||
          claims?['dataPartition'] != dataPartition) {
        throw StateError('review_session_claims_invalid');
      }

      final prepared = await _functions
          .httpsCallable('preparePlayReviewSession')
          .call(const <String, dynamic>{});
      final preparedData = _asMap(prepared.data);
      if (preparedData['ok'] != true ||
          preparedData['reviewerUid'] != reviewerUid) {
        throw StateError('review_session_prepare_failed');
      }

      await Future.wait([
        _storageService.saveAppUserId(reviewerUid),
        _storageService.saveUserId(reviewerUid),
        // Legacy-named cache key is still how matching services locate the
        // canonical app UID. It does not imply a Kakao identity.
        _storageService.saveKakaoUserId(reviewerUid),
      ]);
      return PlayReviewSession(
        reviewerUid: reviewerUid,
        blindMeetingId:
            preparedData['blindMeetingId']?.toString() ??
            'play-review-blind-meeting-v1',
      );
    } catch (_) {
      await _firebaseAuth.signOut();
      rethrow;
    }
  }

  static Map<String, dynamic> _asMap(Object? value) {
    if (value is! Map) return const <String, dynamic>{};
    return Map<String, dynamic>.from(value);
  }
}
