import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

/// 카카오 인증 화면 (Mock)
class KakaoAuthScreen extends StatefulWidget {
  const KakaoAuthScreen({super.key});

  @override
  State<KakaoAuthScreen> createState() => _KakaoAuthScreenState();
}

class _KakaoAuthScreenState extends State<KakaoAuthScreen> {
  bool _isLoading = false;

  void _kakaoLogin() {
    setState(() => _isLoading = true);
    // TODO: Kakao SDK integration
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() => _isLoading = false);
        context.push('/student-verification');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: const SeolAppBar(title: '카카오 인증'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('카카오 계정으로\n간편 인증', style: SeolTypography.h2),
              const SizedBox(height: 8),
              Text(
                '카카오 계정으로 빠르게 인증해보세요',
                style: SeolTypography.bodyMedium.copyWith(
                  color: SeolColors.textSecondary,
                ),
              ),
              const Spacer(),
              // Kakao Logo
              Center(
                child: Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEE500),
                    borderRadius: BorderRadius.circular(30),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFFEE500).withValues(alpha: 0.4),
                        blurRadius: 24,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.chat_bubble,
                    size: 60,
                    color: Color(0xFF3A1D1D),
                  ),
                ),
              ),
              const Spacer(),
              // Info
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: SeolColors.backgroundGrey,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('카카오 인증 시 제공 정보', style: SeolTypography.labelMedium),
                    const SizedBox(height: 8),
                    _InfoRow(icon: Icons.person_outline, text: '닉네임'),
                    const SizedBox(height: 4),
                    _InfoRow(icon: Icons.email_outlined, text: '이메일'),
                    const SizedBox(height: 4),
                    _InfoRow(icon: Icons.cake_outlined, text: '생년월일'),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              // Kakao Login Button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _kakaoLogin,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFEE500),
                    foregroundColor: const Color(0xFF3A1D1D),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    elevation: 0,
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Color(0xFF3A1D1D),
                          ),
                        )
                      : Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.chat_bubble, size: 20),
                            const SizedBox(width: 8),
                            Text(
                              '카카오로 계속하기',
                              style: SeolTypography.buttonText.copyWith(
                                color: const Color(0xFF3A1D1D),
                              ),
                            ),
                          ],
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: SeolColors.textSecondary),
        const SizedBox(width: 8),
        Text(text, style: SeolTypography.bodySmall),
      ],
    );
  }
}
