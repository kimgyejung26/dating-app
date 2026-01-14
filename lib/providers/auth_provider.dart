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

  UserModel? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated;

  AuthProvider() {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      final userId = await _storageService.getUserId();
      if (userId != null) {
        _currentUser = await _authService.getUser(userId);
        _isAuthenticated = _currentUser != null;
      }
    } catch (e) {
      debugPrint('Error checking auth status: $e');
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

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storageService.clearUserId();
      _currentUser = null;
      _isAuthenticated = false;
    } catch (e) {
      debugPrint('Error during logout: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
