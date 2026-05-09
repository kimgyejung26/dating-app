import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

/// 인증 방식 선택 화면 (휴대폰/카카오)
class AuthChoiceScreen extends StatelessWidget {
  const AuthChoiceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: const SeolAppBar(title: '본인 인증'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('본인 인증을\n진행해주세요', style: SeolTypography.h2),
              const SizedBox(height: 8),
              Text(
                '안전한 소개팅 환경을 위해 본인 인증이 필요해요',
                style: SeolTypography.bodyMedium.copyWith(
                  color: SeolColors.textSecondary,
                ),
              ),
              const SizedBox(height: 48),
              // Phone Auth
              _AuthOption(
                icon: Icons.phone_android,
                title: '휴대폰 인증',
                subtitle: '휴대폰 번호로 본인 확인',
                onTap: () => context.push('/phone-auth'),
              ),
              const SizedBox(height: 16),
              // Kakao Auth
              _AuthOption(
                icon: Icons.chat_bubble,
                title: '카카오 인증',
                subtitle: '카카오 계정으로 간편 인증',
                backgroundColor: const Color(0xFFFEE500),
                iconColor: const Color(0xFF3A1D1D),
                onTap: () => context.push('/kakao-auth'),
              ),
              const Spacer(),
              // Info
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: SeolColors.secondaryLight.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.shield_outlined,
                      color: SeolColors.secondary,
                      size: 24,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '인증 정보는 안전하게 보호되며\n학생 인증에만 사용됩니다',
                        style: SeolTypography.bodySmall.copyWith(
                          color: SeolColors.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuthOption extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color? backgroundColor;
  final Color? iconColor;
  final VoidCallback onTap;

  const _AuthOption({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.backgroundColor,
    this.iconColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SeolCard(
      onTap: onTap,
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: backgroundColor ?? SeolColors.primarySoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, size: 28, color: iconColor ?? SeolColors.primary),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: SeolTypography.labelLarge),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: SeolTypography.bodySmall.copyWith(
                    color: SeolColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: SeolColors.textTertiary),
        ],
      ),
    );
  }
}
