import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

class StudentVerificationScreen extends StatefulWidget {
  const StudentVerificationScreen({super.key});

  @override
  State<StudentVerificationScreen> createState() =>
      _StudentVerificationScreenState();
}

class _StudentVerificationScreenState extends State<StudentVerificationScreen> {
  final _emailController = TextEditingController();
  bool _isVerifying = false;
  bool _emailSent = false;
  String? _selectedUniversity;

  final List<String> _universities = [
    '연세대학교',
    '고려대학교',
    '서울대학교',
    '성균관대학교',
    '한양대학교',
    '이화여자대학교',
    '중앙대학교',
    '경희대학교',
    '서강대학교',
    '한국외국어대학교',
  ];

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  void _sendVerificationEmail() {
    setState(() => _isVerifying = true);
    // TODO: API call to send verification email
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() {
          _isVerifying = false;
          _emailSent = true;
        });
      }
    });
  }

  void _verifyAndProceed() {
    setState(() => _isVerifying = true);
    // TODO: API call to verify email
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() => _isVerifying = false);
        context.push('/initial-setup');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: const SeolAppBar(title: '재학생 인증'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('대학 재학생 인증을\n진행해주세요', style: SeolTypography.h2),
              const SizedBox(height: 8),
              Text(
                '대학교 이메일로 재학생 인증을 해주세요',
                style: SeolTypography.bodyMedium.copyWith(
                  color: SeolColors.textSecondary,
                ),
              ),
              const SizedBox(height: 32),
              // University Dropdown
              _buildUniversityDropdown(),
              const SizedBox(height: 16),
              // Email Input
              _buildEmailInput(),
              if (_emailSent) ...[
                const SizedBox(height: 24),
                _buildSuccessMessage(),
              ],
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
                      Icons.school_outlined,
                      color: SeolColors.secondary,
                      size: 24,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '대학 이메일로 인증된 사용자만\n설레연 서비스를 이용할 수 있어요',
                        style: SeolTypography.bodySmall.copyWith(
                          color: SeolColors.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SeolButton(
                text: _emailSent ? '인증 완료' : '인증 메일 보내기',
                isLoading: _isVerifying,
                onPressed:
                    _selectedUniversity != null &&
                        _emailController.text.isNotEmpty
                    ? (_emailSent ? _verifyAndProceed : _sendVerificationEmail)
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildUniversityDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        border: Border.all(color: SeolColors.borderLight),
        borderRadius: BorderRadius.circular(14),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _selectedUniversity,
          hint: Text(
            '대학교 선택',
            style: SeolTypography.bodyLarge.copyWith(
              color: SeolColors.textHint,
            ),
          ),
          isExpanded: true,
          icon: const Icon(Icons.keyboard_arrow_down),
          items: _universities.map((uni) {
            return DropdownMenuItem(
              value: uni,
              child: Text(uni, style: SeolTypography.bodyLarge),
            );
          }).toList(),
          onChanged: (value) => setState(() => _selectedUniversity = value),
        ),
      ),
    );
  }

  Widget _buildEmailInput() {
    final emailSuffix = _selectedUniversity != null
        ? '@${_getEmailDomain(_selectedUniversity!)}'
        : '';

    return TextField(
      controller: _emailController,
      keyboardType: TextInputType.emailAddress,
      style: SeolTypography.bodyLarge,
      decoration: InputDecoration(
        hintText: '학교 이메일 ID',
        hintStyle: SeolTypography.bodyLarge.copyWith(
          color: SeolColors.textHint,
        ),
        suffixText: emailSuffix,
        suffixStyle: SeolTypography.bodyMedium.copyWith(
          color: SeolColors.textSecondary,
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
          horizontal: 16,
          vertical: 16,
        ),
      ),
      onChanged: (_) => setState(() {}),
    );
  }

  Widget _buildSuccessMessage() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SeolColors.tagFirstMeet,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: SeolColors.success, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '인증 메일을 발송했어요!',
                  style: SeolTypography.labelMedium.copyWith(
                    color: SeolColors.success,
                  ),
                ),
                const SizedBox(height: 4),
                Text('이메일을 확인하고 인증을 완료해주세요', style: SeolTypography.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _getEmailDomain(String university) {
    switch (university) {
      case '연세대학교':
        return 'yonsei.ac.kr';
      case '고려대학교':
        return 'korea.ac.kr';
      case '서울대학교':
        return 'snu.ac.kr';
      case '성균관대학교':
        return 'skku.edu';
      case '한양대학교':
        return 'hanyang.ac.kr';
      case '이화여자대학교':
        return 'ewha.ac.kr';
      case '중앙대학교':
        return 'cau.ac.kr';
      case '경희대학교':
        return 'khu.ac.kr';
      case '서강대학교':
        return 'sogang.ac.kr';
      case '한국외국어대학교':
        return 'hufs.ac.kr';
      default:
        return 'university.ac.kr';
    }
  }
}
