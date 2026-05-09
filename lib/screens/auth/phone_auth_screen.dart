import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

/// 휴대폰 인증 화면
class PhoneAuthScreen extends StatefulWidget {
  const PhoneAuthScreen({super.key});

  @override
  State<PhoneAuthScreen> createState() => _PhoneAuthScreenState();
}

class _PhoneAuthScreenState extends State<PhoneAuthScreen> {
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();
  bool _codeSent = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  void _sendCode() {
    setState(() {
      _isLoading = true;
    });
    // TODO: API call to send verification code
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() {
          _codeSent = true;
          _isLoading = false;
        });
      }
    });
  }

  void _verifyCode() {
    setState(() {
      _isLoading = true;
    });
    // TODO: API call to verify code
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        context.push('/student-verification');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: const SeolAppBar(title: '휴대폰 인증'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _codeSent ? '인증번호를\n입력해주세요' : '휴대폰 번호를\n입력해주세요',
                style: SeolTypography.h2,
              ),
              const SizedBox(height: 8),
              Text(
                _codeSent ? '발송된 6자리 인증번호를 입력해주세요' : '인증번호를 받을 휴대폰 번호를 입력해주세요',
                style: SeolTypography.bodyMedium.copyWith(
                  color: SeolColors.textSecondary,
                ),
              ),
              const SizedBox(height: 40),
              // Phone Number Input
              if (!_codeSent) ...[
                _buildPhoneInput(),
              ] else ...[
                // Code Input
                _buildCodeInput(),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('인증번호가 오지 않나요?', style: SeolTypography.bodySmall),
                    TextButton(
                      onPressed: _sendCode,
                      child: Text(
                        '재발송',
                        style: SeolTypography.labelMedium.copyWith(
                          color: SeolColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              const Spacer(),
              SeolButton(
                text: _codeSent ? '인증하기' : '인증번호 받기',
                isLoading: _isLoading,
                onPressed: _codeSent
                    ? (_codeController.text.length == 6 ? _verifyCode : null)
                    : (_phoneController.text.length >= 10 ? _sendCode : null),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPhoneInput() {
    return TextField(
      controller: _phoneController,
      keyboardType: TextInputType.phone,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(11),
      ],
      style: SeolTypography.h3,
      decoration: InputDecoration(
        hintText: '010-0000-0000',
        hintStyle: SeolTypography.h3.copyWith(color: SeolColors.textHint),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.borderLight),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.borderLight),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 20,
          vertical: 18,
        ),
      ),
      onChanged: (_) => setState(() {}),
    );
  }

  Widget _buildCodeInput() {
    return TextField(
      controller: _codeController,
      keyboardType: TextInputType.number,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(6),
      ],
      textAlign: TextAlign.center,
      style: SeolTypography.h2.copyWith(letterSpacing: 12),
      decoration: InputDecoration(
        hintText: '● ● ● ● ● ●',
        hintStyle: SeolTypography.h3.copyWith(
          color: SeolColors.textHint,
          letterSpacing: 12,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.borderLight),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.borderLight),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: SeolColors.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 20,
          vertical: 18,
        ),
      ),
      onChanged: (_) => setState(() {}),
    );
  }
}
