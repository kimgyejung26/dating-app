import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/user_service.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  static final _userService = UserService();

  @override
  Widget build(BuildContext context) {
    final kakaoUserId = context.select<AuthProvider, String?>(
      (provider) => provider.kakaoUserId,
    );

    return Scaffold(
      appBar: AppBar(title: const Text('내 페이지')),
      body: ListView(
        children: [
          // Profile Header
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: FutureBuilder<Map<String, dynamic>?>(
              future: kakaoUserId != null
                  ? _userService.getUserProfile(kakaoUserId)
                  : Future.value(null),
              builder: (context, snapshot) {
                final isLoading =
                    kakaoUserId != null &&
                    snapshot.connectionState == ConnectionState.waiting;
                final data = snapshot.data;
                final displayName = data?['name']?.toString() ?? '사용자 이름';
                final displayNickname = data?['nickname']?.toString() ?? '닉네임';
                return Column(
                  children: [
                    const CircleAvatar(
                      radius: 50,
                      child: Icon(Icons.person, size: 50),
                    ),
                    const SizedBox(height: 16),
                    if (isLoading)
                      const CircularProgressIndicator()
                    else ...[
                      Text(
                        displayName,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        displayNickname,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),

          const Divider(),

          // Menu Items
          _buildMenuItem(
            icon: Icons.person_outline,
            title: '프로필',
            onTap: () {
              // TODO: Navigate to profile edit
            },
          ),
          _buildMenuItem(
            icon: Icons.settings,
            title: '환경설정',
            onTap: () {
              // TODO: Navigate to settings
            },
          ),
          _buildMenuItem(
            icon: Icons.account_balance_wallet,
            title: '머니 충전',
            onTap: () {
              // TODO: Navigate to money charge
            },
          ),
          _buildMenuItem(
            icon: Icons.bar_chart,
            title: '나의 이상형 통계 보고서',
            onTap: () {
              // TODO: Navigate to statistics
            },
          ),
          _buildMenuItem(
            icon: Icons.block,
            title: '아는 사람 피하기',
            onTap: () {
              // TODO: Navigate to block contacts
            },
          ),
          _buildMenuItem(
            icon: Icons.description,
            title: '약관 및 정책',
            onTap: () {
              // TODO: Navigate to terms
            },
          ),

          const Divider(),

          // Logout
          _buildMenuItem(
            icon: Icons.logout,
            title: '로그아웃',
            onTap: () {
              // TODO: Implement logout
            },
            textColor: Colors.red,
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    Color? textColor,
  }) {
    return ListTile(
      leading: Icon(icon, color: textColor),
      title: Text(title, style: TextStyle(color: textColor)),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
