import '../models/user_model.dart';
// TODO: Uncomment when implementing actual API calls
// import 'api_service.dart';
import 'package:uuid/uuid.dart';

class AuthService {
  // TODO: Uncomment when implementing actual API calls
  // final ApiService _apiService = ApiService();
  final _uuid = const Uuid();

  Future<UserModel?> signUp({
    required String phoneNumber,
    required String verificationCode,
    String? kakaoToken,
  }) async {
    try {
      // TODO: Implement actual API call
      // For now, return a mock user
      final user = UserModel(
        id: _uuid.v4(),
        phoneNumber: phoneNumber,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      // Simulate API call
      await Future.delayed(const Duration(seconds: 1));

      return user;
    } catch (e) {
      throw Exception('Sign up failed: $e');
    }
  }

  Future<bool> verifyStudent({
    required String userId,
    required String portalId,
    required String portalPassword,
  }) async {
    try {
      // TODO: Implement actual Yonsei Portal verification
      // For now, simulate verification
      await Future.delayed(const Duration(seconds: 1));
      return true;
    } catch (e) {
      throw Exception('Student verification failed: $e');
    }
  }

  Future<UserModel?> getUser(String userId) async {
    try {
      // TODO: Implement actual API call
      await Future.delayed(const Duration(milliseconds: 500));
      return null; // Return null if user not found
    } catch (e) {
      throw Exception('Get user failed: $e');
    }
  }

  Future<void> updateUser(UserModel user) async {
    try {
      // TODO: Implement actual API call
      await Future.delayed(const Duration(milliseconds: 500));
    } catch (e) {
      throw Exception('Update user failed: $e');
    }
  }
}
