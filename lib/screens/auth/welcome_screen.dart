import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      useGradient: true,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            children: [
              const Spacer(flex: 2),
              // Logo & Branding
              _buildLogo(),
              const SizedBox(height: 24),
              _buildTagline(),
              const Spacer(flex: 3),
              // CTA Buttons
              _buildButtons(context),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLogo() {
    return Column(
      children: [
        Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            gradient: SeolColors.primaryGradient,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: SeolColors.primary.withValues(alpha: 0.4),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: const Icon(
            Icons.favorite,
            color: SeolColors.textWhite,
            size: 48,
          ),
        ),
        const SizedBox(height: 24),
        ShaderMask(
          shaderCallback: (bounds) =>
              SeolColors.primaryGradient.createShader(bounds),
          child: const Text(
            '설레연',
            style: TextStyle(
              fontSize: 48,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              letterSpacing: -1,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTagline() {
    return Column(
      children: [
        Text(
          '대학생 전용 프리미엄 소개팅',
          style: SeolTypography.bodyLarge.copyWith(
            color: SeolColors.textSecondary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          '진정한 만남이 시작되는 곳',
          style: SeolTypography.bodyMedium.copyWith(
            color: SeolColors.textTertiary,
          ),
        ),
      ],
    );
  }

  Widget _buildButtons(BuildContext context) {
    return Column(
      children: [
        SeolButton(text: '시작하기', onPressed: () => context.push('/terms')),
        const SizedBox(height: 12),
        SeolButton(
          text: '이미 계정이 있어요',
          type: SeolButtonType.ghost,
          onPressed: () => context.push('/auth-choice'),
        ),
      ],
    );
  }
}
