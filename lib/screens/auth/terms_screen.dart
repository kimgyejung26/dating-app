import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';

class TermsScreen extends StatefulWidget {
  const TermsScreen({super.key});

  @override
  State<TermsScreen> createState() => _TermsScreenState();
}

class _TermsScreenState extends State<TermsScreen> {
  bool _allAgreed = false;
  bool _serviceTerms = false;
  bool _privacyPolicy = false;
  bool _ageVerification = false;
  bool _marketingOptIn = false;

  bool get _requiredAgreed =>
      _serviceTerms && _privacyPolicy && _ageVerification;

  void _toggleAll(bool? value) {
    setState(() {
      _allAgreed = value ?? false;
      _serviceTerms = _allAgreed;
      _privacyPolicy = _allAgreed;
      _ageVerification = _allAgreed;
      _marketingOptIn = _allAgreed;
    });
  }

  void _updateAllAgreed() {
    setState(() {
      _allAgreed =
          _serviceTerms &&
          _privacyPolicy &&
          _ageVerification &&
          _marketingOptIn;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: const SeolAppBar(title: '약관 동의'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('서비스 이용을 위해\n약관에 동의해주세요', style: SeolTypography.h2),
              const SizedBox(height: 32),
              // All Agree
              _buildAllAgreeItem(),
              const SizedBox(height: 16),
              const Divider(color: SeolColors.divider),
              const SizedBox(height: 16),
              // Individual Terms
              _buildTermItem(
                title: '서비스 이용약관',
                isRequired: true,
                isChecked: _serviceTerms,
                onChanged: (v) {
                  setState(() => _serviceTerms = v ?? false);
                  _updateAllAgreed();
                },
              ),
              const SizedBox(height: 12),
              _buildTermItem(
                title: '개인정보 처리방침',
                isRequired: true,
                isChecked: _privacyPolicy,
                onChanged: (v) {
                  setState(() => _privacyPolicy = v ?? false);
                  _updateAllAgreed();
                },
              ),
              const SizedBox(height: 12),
              _buildTermItem(
                title: '만 18세 이상 확인',
                isRequired: true,
                isChecked: _ageVerification,
                onChanged: (v) {
                  setState(() => _ageVerification = v ?? false);
                  _updateAllAgreed();
                },
              ),
              const SizedBox(height: 12),
              _buildTermItem(
                title: '마케팅 정보 수신',
                isRequired: false,
                isChecked: _marketingOptIn,
                onChanged: (v) {
                  setState(() => _marketingOptIn = v ?? false);
                  _updateAllAgreed();
                },
              ),
              const Spacer(),
              // Warning
              if (!_requiredAgreed)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: SeolColors.tagWorry,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.info_outline,
                        color: SeolColors.warning,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '필수 약관에 동의해 주세요',
                        style: SeolTypography.bodySmall.copyWith(
                          color: SeolColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              SeolButton(
                text: '다음',
                onPressed: _requiredAgreed
                    ? () => context.push('/auth-choice')
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAllAgreeItem() {
    return InkWell(
      onTap: () => _toggleAll(!_allAgreed),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: _allAgreed
              ? SeolColors.primarySoft
              : SeolColors.backgroundGrey,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _allAgreed ? SeolColors.primary : SeolColors.borderLight,
          ),
        ),
        child: Row(
          children: [
            _buildCheckbox(_allAgreed, (v) => _toggleAll(v)),
            const SizedBox(width: 12),
            Text(
              '전체 동의',
              style: SeolTypography.labelLarge.copyWith(
                color: _allAgreed ? SeolColors.primary : SeolColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTermItem({
    required String title,
    required bool isRequired,
    required bool isChecked,
    required ValueChanged<bool?> onChanged,
  }) {
    return InkWell(
      onTap: () => onChanged(!isChecked),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            _buildCheckbox(isChecked, onChanged),
            const SizedBox(width: 12),
            Expanded(
              child: Row(
                children: [
                  Text(title, style: SeolTypography.bodyMedium),
                  const SizedBox(width: 6),
                  Text(
                    isRequired ? '(필수)' : '(선택)',
                    style: SeolTypography.bodySmall.copyWith(
                      color: isRequired
                          ? SeolColors.primary
                          : SeolColors.textTertiary,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: () {
                // TODO: Show terms detail
              },
              icon: const Icon(
                Icons.chevron_right,
                color: SeolColors.textTertiary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCheckbox(bool value, ValueChanged<bool?> onChanged) {
    return SizedBox(
      width: 24,
      height: 24,
      child: Checkbox(
        value: value,
        onChanged: onChanged,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        activeColor: SeolColors.primary,
        side: const BorderSide(color: SeolColors.borderMedium, width: 1.5),
      ),
    );
  }
}
