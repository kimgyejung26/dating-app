import 'package:flutter/foundation.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';

class AuthProvider with ChangeNotifier {
  final AuthService _authService = AuthService();
  final StorageService _storageService = StorageService();

  UserModel? _currentUser;
  bool _isLoading = false;
  bool _isAuthenticated = false;
  String? _kakaoUserId;
  Map<String, dynamic>? _kakaoUserInfo;
  bool _needsInitialSetup = true;
  bool _hasSeenTutorial = false;

  UserModel? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated;
  String? get kakaoUserId => _kakaoUserId;
  Map<String, dynamic>? get kakaoUserInfo => _kakaoUserInfo;
  bool get needsInitialSetup => _needsInitialSetup;
  bool get hasSeenTutorial => _hasSeenTutorial;

  AuthProvider() {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storageService.clearKakaoUserId();
      await _storageService.clearUserId();
      _kakaoUserId = null;
      _isAuthenticated = false;
      _needsInitialSetup = true;
      _hasSeenTutorial = false;

      final kakaoUserId = await _storageService.getKakaoUserId();
      if (kakaoUserId != null &&
          await _authService.kakaoUserExists(kakaoUserId)) {
        _kakaoUserId = kakaoUserId;
        _isAuthenticated = true;
        _needsInitialSetup = !(await _authService.isInitialSetupComplete(
          kakaoUserId,
        ));
        _hasSeenTutorial = await _authService.hasSeenTutorial(kakaoUserId);
      } else {
        await _storageService.clearKakaoUserId();
        _kakaoUserId = null;
        _isAuthenticated = false;
        _needsInitialSetup = true;
        _hasSeenTutorial = false;
      }
    } catch (e) {
      debugPrint('Error checking auth status: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> setKakaoLogin(
    String kakaoUserId, {
    Map<String, dynamic>? userInfo,
  }) async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storageService.saveKakaoUserId(kakaoUserId);
      _kakaoUserId = kakaoUserId;
      _isAuthenticated = true;
      _kakaoUserInfo = userInfo;
      _needsInitialSetup = !(await _authService.isInitialSetupComplete(
        kakaoUserId,
      ));
      _hasSeenTutorial = await _authService.hasSeenTutorial(kakaoUserId);
    } catch (e) {
      debugPrint('Error saving kakao user id: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> signUp({
    required String phoneNumber,
    required String verificationCode,
    String? kakaoToken,
  }) async {
    _isLoading = true;
    notifyListeners();

    try {
      final user = await _authService.signUp(
        phoneNumber: phoneNumber,
        verificationCode: verificationCode,
        kakaoToken: kakaoToken,
      );

      if (user != null) {
        _currentUser = user;
        _isAuthenticated = true;
        await _storageService.saveUserId(user.id);
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error during signup: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> verifyStudent(String portalId, String portalPassword) async {
    if (_currentUser == null) return false;

    _isLoading = true;
    notifyListeners();

    try {
      final verified = await _authService.verifyStudent(
        userId: _currentUser!.id,
        portalId: portalId,
        portalPassword: portalPassword,
      );

      if (verified) {
        _currentUser = _currentUser!.copyWith(isStudentVerified: true);
        await _authService.updateUser(_currentUser!);
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error during student verification: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> completeInitialSetup(UserModel updatedUser) async {
    if (_currentUser == null) return false;

    _isLoading = true;
    notifyListeners();

    try {
      final user = updatedUser.copyWith(
        isInitialSetupComplete: true,
        updatedAt: DateTime.now(),
      );

      await _authService.updateUser(user);
      _currentUser = user;
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Error completing initial setup: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void markInitialSetupComplete() {
    _needsInitialSetup = false;
    notifyListeners();
  }

  Future<void> markTutorialSeen() async {
    final kakaoUserId = _kakaoUserId;
    if (kakaoUserId == null) return;
    await _authService.setTutorialSeen(kakaoUserId);
    _hasSeenTutorial = true;
    notifyListeners();
  }

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storageService.clearUserId();
      await _storageService.clearKakaoUserId();
      _currentUser = null;
      _isAuthenticated = false;
      _kakaoUserId = null;
      _hasSeenTutorial = false;
    } catch (e) {
      debugPrint('Error during logout: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
