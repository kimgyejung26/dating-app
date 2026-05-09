import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

/// 프로필 초기 설정 화면 (위자드 형태)
class InitialSetupScreen extends StatefulWidget {
  const InitialSetupScreen({super.key});

  @override
  State<InitialSetupScreen> createState() => _InitialSetupScreenState();
}

class _InitialSetupScreenState extends State<InitialSetupScreen> {
  int _currentStep = 0;

  // Step 1: Basic Info
  final _nicknameController = TextEditingController();
  String? _selectedGender;
  int? _birthYear;

  // Step 2: Department & Grade
  String? _selectedDepartment;
  int? _selectedGrade;

  // Step 3: MBTI & Height
  String? _selectedMbti;
  int? _height;

  // Step 4: Interests
  final List<String> _selectedInterests = [];

  // Step 5: Introduction
  final _introController = TextEditingController();

  static const List<String> _departments = [
    '경영학과',
    '경제학과',
    '컴퓨터공학과',
    '심리학과',
    '의예과',
    '간호학과',
    '문헌정보학과',
    '영어영문학과',
    '신문방송학과',
    '사회학과',
    '정치외교학과',
    '법학과',
    '기계공학과',
    '전기전자공학과',
    '화학공학과',
    '기타',
  ];

  static const List<String> _mbtiTypes = [
    'INTJ',
    'INTP',
    'ENTJ',
    'ENTP',
    'INFJ',
    'INFP',
    'ENFJ',
    'ENFP',
    'ISTJ',
    'ISFJ',
    'ESTJ',
    'ESFJ',
    'ISTP',
    'ISFP',
    'ESTP',
    'ESFP',
  ];

  static const List<String> _interestOptions = [
    '여행',
    '맛집',
    '운동',
    '독서',
    '영화',
    '음악',
    '게임',
    '카페',
    '쇼핑',
    '드라이브',
    '사진',
    '요리',
    '반려동물',
    '패션',
    '피트니스',
    '러닝',
    '등산',
    '캠핑',
  ];

  @override
  void dispose() {
    _nicknameController.dispose();
    _introController.dispose();
    super.dispose();
  }

  void _nextStep() {
    if (_currentStep < 4) {
      setState(() => _currentStep++);
    } else {
      // Complete setup - TODO: Save profile data
      // Profile includes: nickname, gender, birthYear, department, grade, mbti, height, interests, intro
      debugPrint(
        'Profile: ${_nicknameController.text}, $_selectedGender, $_birthYear, $_selectedDepartment, $_selectedGrade, $_selectedMbti, $_height, $_selectedInterests',
      );
      context.pushReplacement('/tutorial');
    }
  }

  void _previousStep() {
    if (_currentStep > 0) {
      setState(() => _currentStep--);
    }
  }

  bool get _canProceed {
    switch (_currentStep) {
      case 0:
        return _nicknameController.text.isNotEmpty &&
            _selectedGender != null &&
            _birthYear != null;
      case 1:
        return _selectedDepartment != null && _selectedGrade != null;
      case 2:
        return true; // MBTI and height are optional
      case 3:
        return _selectedInterests.isNotEmpty;
      case 4:
        return true; // Introduction is optional
      default:
        return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: SeolAppBar(
        title: '프로필 설정',
        showBackButton: _currentStep > 0,
        onBackPressed: _currentStep > 0 ? _previousStep : null,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Progress Indicator
            _buildProgressIndicator(),
            // Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: _buildStepContent(),
              ),
            ),
            // Next Button
            Padding(
              padding: const EdgeInsets.all(24),
              child: SeolButton(
                text: _currentStep < 4 ? '다음' : '완료',
                onPressed: _canProceed ? _nextStep : null,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressIndicator() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Row(
        children: List.generate(5, (index) {
          final isActive = index <= _currentStep;
          return Expanded(
            child: Container(
              height: 4,
              margin: EdgeInsets.only(right: index < 4 ? 8 : 0),
              decoration: BoxDecoration(
                color: isActive ? SeolColors.primary : SeolColors.borderLight,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 0:
        return _buildBasicInfoStep();
      case 1:
        return _buildDepartmentStep();
      case 2:
        return _buildMbtiStep();
      case 3:
        return _buildInterestsStep();
      case 4:
        return _buildIntroductionStep();
      default:
        return const SizedBox();
    }
  }

  Widget _buildBasicInfoStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('기본 정보를\n입력해주세요', style: SeolTypography.h2),
        const SizedBox(height: 32),
        // Nickname
        Text('닉네임', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _nicknameController,
          style: SeolTypography.bodyLarge,
          decoration: _inputDecoration('2-10자 이내'),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 24),
        // Gender
        Text('성별', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _buildSelectionButton(
                label: '남성',
                isSelected: _selectedGender == '남성',
                onTap: () => setState(() => _selectedGender = '남성'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildSelectionButton(
                label: '여성',
                isSelected: _selectedGender == '여성',
                onTap: () => setState(() => _selectedGender = '여성'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        // Birth Year
        Text('출생연도', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        _buildDropdown(
          value: _birthYear?.toString(),
          hint: '선택',
          items: List.generate(10, (i) => (2006 - i).toString()),
          onChanged: (v) => setState(() => _birthYear = int.tryParse(v ?? '')),
        ),
      ],
    );
  }

  Widget _buildDepartmentStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('학과 정보를\n입력해주세요', style: SeolTypography.h2),
        const SizedBox(height: 32),
        Text('학과', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        _buildDropdown(
          value: _selectedDepartment,
          hint: '학과 선택',
          items: _departments,
          onChanged: (v) => setState(() => _selectedDepartment = v),
        ),
        const SizedBox(height: 24),
        Text('학년', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        Row(
          children: List.generate(4, (i) {
            final grade = i + 1;
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(right: i < 3 ? 8 : 0),
                child: _buildSelectionButton(
                  label: '$grade학년',
                  isSelected: _selectedGrade == grade,
                  onTap: () => setState(() => _selectedGrade = grade),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }

  Widget _buildMbtiStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('더 알려주세요\n(선택사항)', style: SeolTypography.h2),
        const SizedBox(height: 32),
        Text('MBTI', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _mbtiTypes.map((mbti) {
            return SeolChip(
              label: mbti,
              type: SeolChipType.selection,
              isSelected: _selectedMbti == mbti,
              onTap: () => setState(() => _selectedMbti = mbti),
            );
          }).toList(),
        ),
        const SizedBox(height: 24),
        Text('키 (cm)', style: SeolTypography.labelMedium),
        const SizedBox(height: 8),
        TextField(
          keyboardType: TextInputType.number,
          style: SeolTypography.bodyLarge,
          decoration: _inputDecoration('ex) 170'),
          onChanged: (v) => setState(() => _height = int.tryParse(v)),
        ),
      ],
    );
  }

  Widget _buildInterestsStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('관심사를\n선택해주세요', style: SeolTypography.h2),
        const SizedBox(height: 8),
        Text(
          '최소 1개 이상 선택해주세요',
          style: SeolTypography.bodyMedium.copyWith(
            color: SeolColors.textSecondary,
          ),
        ),
        const SizedBox(height: 32),
        Wrap(
          spacing: 8,
          runSpacing: 10,
          children: _interestOptions.map((interest) {
            final isSelected = _selectedInterests.contains(interest);
            return SeolChip(
              label: interest,
              type: SeolChipType.selection,
              isSelected: isSelected,
              onTap: () {
                setState(() {
                  if (isSelected) {
                    _selectedInterests.remove(interest);
                  } else {
                    _selectedInterests.add(interest);
                  }
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildIntroductionStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('자기소개를\n작성해주세요', style: SeolTypography.h2),
        const SizedBox(height: 8),
        Text(
          '상대방에게 보여질 소개글이에요 (선택)',
          style: SeolTypography.bodyMedium.copyWith(
            color: SeolColors.textSecondary,
          ),
        ),
        const SizedBox(height: 32),
        TextField(
          controller: _introController,
          maxLines: 5,
          maxLength: 200,
          style: SeolTypography.bodyLarge,
          decoration: InputDecoration(
            hintText: '자신을 소개해주세요...',
            hintStyle: SeolTypography.bodyLarge.copyWith(
              color: SeolColors.textHint,
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
          ),
        ),
      ],
    );
  }

  Widget _buildSelectionButton({
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? SeolColors.primarySoft
              : SeolColors.backgroundWhite,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? SeolColors.primary : SeolColors.borderLight,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: SeolTypography.labelMedium.copyWith(
              color: isSelected ? SeolColors.primary : SeolColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDropdown({
    required String? value,
    required String hint,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        border: Border.all(color: SeolColors.borderLight),
        borderRadius: BorderRadius.circular(14),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          hint: Text(
            hint,
            style: SeolTypography.bodyLarge.copyWith(
              color: SeolColors.textHint,
            ),
          ),
          isExpanded: true,
          items: items
              .map((item) => DropdownMenuItem(value: item, child: Text(item)))
              .toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: SeolTypography.bodyLarge.copyWith(color: SeolColors.textHint),
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
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    );
  }
}
