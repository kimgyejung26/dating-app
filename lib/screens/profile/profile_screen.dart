import 'package:flutter/material.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('내 페이지'),
      ),
      body: ListView(
        children: [
          // Profile Header
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 50,
                  child: Icon(Icons.person, size: 50),
                ),
                SizedBox(height: 16),
                Text(
                  '사용자 이름',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  '닉네임',
                  style: TextStyle(
                    color: Colors.grey,
                  ),
                ),
              ],
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
      title: Text(
        title,
        style: TextStyle(color: textColor),
      ),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
