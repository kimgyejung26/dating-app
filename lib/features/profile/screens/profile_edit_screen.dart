import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart' show Colors, Icons;

import '../../../services/storage_service.dart';
import '../../../services/user_service.dart';
import '../../../router/route_names.dart';

class _AppColors {
  static const Color primary = Color(0xFFFF4B6E);
  static const Color backgroundLight = Color(0xFFF2F4F6);
  static const Color surfaceLight = CupertinoColors.white;
  static const Color textMain = Color(0xFF191F28);
  static const Color textSub = Color(0xFF8B95A1);
  static const Color placeholderBg = Color(0xFFF9FAFB);
}

class ProfileEditScreen extends StatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  State<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends State<ProfileEditScreen> {
  final _userService = UserService();
  final _storageService = StorageService();

  bool _isLoading = true;

  List<String> _photoUrls = [];
  String _selfIntroduction = '';
  List<Map<String, String>> _profileQa = [];
  List<String> _interests = [];
  int? _height;
  String _relationship = '';
  String _mbti = '';
  String _major = '';
  String _nickname = '';

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  String _labelize(String value) {
    switch (value) {
      case 'serious':
        return '진지한 연애를 원해요';
      case 'friend':
        return '가볍게 알아가고 싶어요';
      case 'open':
        return '열린 만남도 괜찮아요';
      case 'liberalArts':
        return '문과 계열';
      case 'science':
        return '이과 계열';
      case 'medical':
        return '메디컬 계열';
      case 'artsSports':
        return '예체능 계열';
      case 'male':
        return '남성';
      case 'female':
        return '여성';
      case 'other':
        return '기타';
      default:
        return value;
    }
  }

  Future<void> _goAndRefresh(String routeName) async {
    await Navigator.of(context).pushNamed(routeName);
    await _loadProfile();
  }

  Future<void> _loadProfile() async {
    final kakaoUserId = await _storageService.getKakaoUserId();
    if (kakaoUserId == null || kakaoUserId.isEmpty) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      return;
    }

    final data = await _userService.getUserProfile(kakaoUserId);
    final onboardingRaw = data?['onboarding'];
    final onboarding = onboardingRaw is Map
        ? Map<String, dynamic>.from(onboardingRaw)
        : <String, dynamic>{};

    final photoUrlsRaw = onboarding['photoUrls'];
    final interestsRaw = onboarding['interests'];
    final profileQaRaw = onboarding['profileQa'];

    if (!mounted) return;

    setState(() {
      _photoUrls = photoUrlsRaw is List
          ? photoUrlsRaw.whereType<String>().toList()
          : [];

      _selfIntroduction = onboarding['selfIntroduction']?.toString() ?? '';

      _interests = interestsRaw is List
          ? interestsRaw.map((e) => _labelize(e.toString())).toList()
          : [];

      _profileQa = profileQaRaw is List
          ? profileQaRaw
                .whereType<Map>()
                .map(
                  (e) => {
                    'question': e['question']?.toString() ?? '',
                    'answer': e['answer']?.toString() ?? '',
                  },
                )
                .toList()
          : [];

      final heightRaw = onboarding['height'];
      _height = heightRaw is num ? heightRaw.toInt() : null;

      _relationship = _labelize(onboarding['relationship']?.toString() ?? '');
      _mbti = onboarding['mbti']?.toString() ?? '';
      _major = _labelize(onboarding['major']?.toString() ?? '');
      _nickname = onboarding['nickname']?.toString() ?? '';

      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      navigationBar: CupertinoNavigationBar(
        backgroundColor: Colors.white.withValues(alpha: 0.9),
        border: const Border(bottom: BorderSide(color: Color(0xFFF2F4F6))),
        leading: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: () => Navigator.of(context).pop(),
          child: const Icon(
            CupertinoIcons.clear,
            color: _AppColors.textMain,
            size: 24,
          ),
        ),
        middle: const Text(
          '프로필 수정',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: _AppColors.textMain,
          ),
        ),
        trailing: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: () {},
          child: const Text(
            '저장',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: Color(0xFF6B7684),
            ),
          ),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: _isLoading
            ? const Center(child: CupertinoActivityIndicator())
            : Column(
                children: [
                  Container(
                    color: Colors.white,
                    child: Row(
                      children: [
                        Expanded(
                          child: Container(
                            decoration: const BoxDecoration(
                              border: Border(
                                bottom: BorderSide(
                                  color: _AppColors.primary,
                                  width: 2,
                                ),
                              ),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            alignment: Alignment.center,
                            child: const Text(
                              '수정하기',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: _AppColors.primary,
                              ),
                            ),
                          ),
                        ),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            alignment: Alignment.center,
                            child: const Text(
                              '미리보기',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: _AppColors.textSub,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      physics: const BouncingScrollPhysics(),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 24,
                      ),
                      child: Column(
                        children: [
                          _PhotoSection(
                            photoUrls: _photoUrls,
                            onTap: () =>
                                _goAndRefresh(RouteNames.onboardingPhoto),
                          ),
                          const SizedBox(height: 16),
                          _SelfIntroSection(
                            introduction: _selfIntroduction,
                            nickname: _nickname,
                            onTap: () =>
                                _goAndRefresh(RouteNames.onboardingSelfIntro),
                          ),
                          const SizedBox(height: 16),
                          _ProfileQuestionsSection(
                            profileQa: _profileQa,
                            onTap: () =>
                                _goAndRefresh(RouteNames.onboardingProfileQa),
                          ),
                          const SizedBox(height: 16),
                          _DetailInfoSection(
                            interests: _interests,
                            height: _height,
                            relationship: _relationship,
                            onInterestsTap: () => _goAndRefresh(
                              RouteNames.onboardingInterestsSelection,
                            ),
                            onHeightTap: () =>
                                _goAndRefresh(RouteNames.onboardingBasicInfo),
                            onRelationshipTap: () =>
                                _goAndRefresh(RouteNames.onboardingBasicInfo),
                          ),
                          const SizedBox(height: 16),
                          _BasicInfoSection(
                            mbti: _mbti,
                            major: _major,
                            onMbtiTap: () =>
                                _goAndRefresh(RouteNames.onboardingBasicInfo),
                            onMajorTap: () =>
                                _goAndRefresh(RouteNames.onboardingMajor),
                          ),
                          const SizedBox(height: 100),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _PhotoSection extends StatelessWidget {
  final List<String> photoUrls;
  final VoidCallback? onTap;

  const _PhotoSection({required this.photoUrls, this.onTap});

  @override
  Widget build(BuildContext context) {
    final photos = List<String?>.generate(
      6,
      (index) => index < photoUrls.length ? photoUrls[index] : null,
    );

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: const [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '프로필 사진',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: _AppColors.textMain,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      '얼굴이 나온 사진 3장은 필수에요',
                      style: TextStyle(fontSize: 14, color: _AppColors.textSub),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth;
                final gap = 8.0;
                final itemWidth = (width - gap * 2) / 3;

                return Column(
                  children: [
                    SizedBox(
                      height: itemWidth * 2 + gap,
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            flex: 2,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(12),
                                  child: photos[0] != null
                                      ? Image.network(
                                          photos[0]!,
                                          fit: BoxFit.cover,
                                        )
                                      : Container(
                                          color: _AppColors.placeholderBg,
                                          child: const Icon(
                                            Icons.person,
                                            size: 48,
                                            color: _AppColors.textSub,
                                          ),
                                        ),
                                ),
                                Positioned(
                                  top: 12,
                                  left: 12,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.black.withValues(
                                        alpha: 0.6,
                                      ),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: const Text(
                                      '메인',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          SizedBox(width: gap),
                          Expanded(
                            flex: 1,
                            child: Column(
                              children: [
                                Expanded(
                                  child: photos[1] != null
                                      ? _PhotoItem(imageUrl: photos[1]!)
                                      : const _AddPhotoButton(),
                                ),
                                SizedBox(height: gap),
                                Expanded(
                                  child: photos[2] != null
                                      ? _PhotoItem(imageUrl: photos[2]!)
                                      : const _AddPhotoButton(),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: gap),
                    SizedBox(
                      height: itemWidth,
                      child: Row(
                        children: [
                          Expanded(
                            child: photos[3] != null
                                ? _PhotoItem(imageUrl: photos[3]!)
                                : const _AddPhotoButton(),
                          ),
                          SizedBox(width: gap),
                          Expanded(
                            child: photos[4] != null
                                ? _PhotoItem(imageUrl: photos[4]!)
                                : const _AddPhotoButton(),
                          ),
                          SizedBox(width: gap),
                          Expanded(
                            child: photos[5] != null
                                ? _PhotoItem(imageUrl: photos[5]!)
                                : const _AddPhotoButton(),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            GestureDetector(
              onTap: () {},
              child: Row(
                children: const [
                  Text(
                    '사진 가이드 참고하기',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: _AppColors.primary,
                    ),
                  ),
                  Icon(
                    Icons.chevron_right,
                    size: 16,
                    color: _AppColors.primary,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoItem extends StatelessWidget {
  final String imageUrl;
  const _PhotoItem({required this.imageUrl});

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Image.network(imageUrl, fit: BoxFit.cover),
        ),
        Positioned(
          top: 4,
          right: 4,
          child: Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.5),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.close, color: Colors.white, size: 12),
          ),
        ),
      ],
    );
  }
}

class _AddPhotoButton extends StatelessWidget {
  const _AddPhotoButton();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB), width: 2),
      ),
      child: const Icon(Icons.add_rounded, color: Color(0xFFD1D5DB), size: 32),
    );
  }
}

class _SelfIntroSection extends StatelessWidget {
  final String introduction;
  final String nickname;
  final VoidCallback? onTap;

  const _SelfIntroSection({
    required this.introduction,
    required this.nickname,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final text = introduction.isEmpty
        ? '${nickname.isEmpty ? '아직' : nickname} 자기소개가 아직 없어요'
        : introduction;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '자기소개',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: _AppColors.textMain,
              ),
            ),
            const SizedBox(height: 16),
            Stack(
              children: [
                Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(minHeight: 128),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: _AppColors.placeholderBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    text,
                    style: const TextStyle(
                      fontSize: 14,
                      height: 1.5,
                      color: _AppColors.textMain,
                    ),
                  ),
                ),
                Positioned(
                  bottom: 12,
                  right: 12,
                  child: Text(
                    '${introduction.length}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: _AppColors.textSub,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              '자기소개 꿀팁',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: _AppColors.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileQuestionsSection extends StatelessWidget {
  final List<Map<String, String>> profileQa;
  final VoidCallback? onTap;

  const _ProfileQuestionsSection({required this.profileQa, this.onTap});

  @override
  Widget build(BuildContext context) {
    final hasQa = profileQa.isNotEmpty;
    final firstQa = hasQa ? profileQa.first : null;
    final question = firstQa?['question'] ?? '프로필 문답 선택하기';
    final answer = firstQa?['answer'] ?? '프로필 문답 작성하기';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Text(
                      '프로필 문답',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: _AppColors.textMain,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: _AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                ),
                const Text(
                  '+10%',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: _AppColors.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE5E7EB)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          question,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: _AppColors.textMain,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          answer,
                          style: const TextStyle(
                            fontSize: 14,
                            color: _AppColors.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 32,
                    height: 32,
                    decoration: const BoxDecoration(
                      color: _AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.add, color: Colors.white, size: 20),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailInfoSection extends StatelessWidget {
  final List<String> interests;
  final int? height;
  final String relationship;
  final VoidCallback? onInterestsTap;
  final VoidCallback? onHeightTap;
  final VoidCallback? onRelationshipTap;

  const _DetailInfoSection({
    required this.interests,
    required this.height,
    required this.relationship,
    this.onInterestsTap,
    this.onHeightTap,
    this.onRelationshipTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _DetailTile(
          title: '관심사',
          content: interests.isEmpty ? '아직 설정되지 않음' : interests.join(', '),
          showIcon: false,
          onTap: onInterestsTap,
        ),
        const SizedBox(height: 16),
        _DetailTile(
          title: '키',
          content: height == null ? '아직 설정되지 않음' : '$height cm',
          icon: Icons.straighten,
          onTap: onHeightTap,
        ),
        const SizedBox(height: 16),
        _DetailTile(
          title: '내가 찾는 관계',
          content: relationship.isEmpty ? '아직 설정되지 않음' : relationship,
          emoji: '😍',
          icon: Icons.visibility,
          onTap: onRelationshipTap,
        ),
      ],
    );
  }
}

class _DetailTile extends StatelessWidget {
  final String title;
  final String content;
  final IconData? icon;
  final String? emoji;
  final bool showIcon;
  final VoidCallback? onTap;

  const _DetailTile({
    required this.title,
    required this.content,
    this.icon,
    this.emoji,
    this.showIcon = true,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: _AppColors.textMain,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              decoration: BoxDecoration(
                color: _AppColors.placeholderBg,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        if (icon != null) ...[
                          Icon(icon, color: Colors.grey[400], size: 20),
                          const SizedBox(width: 8),
                        ],
                        Expanded(
                          child: Text(
                            content,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: _AppColors.textMain,
                            ),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    children: [
                      if (emoji != null) ...[
                        Text(emoji!, style: const TextStyle(fontSize: 20)),
                        const SizedBox(width: 8),
                      ],
                      if (showIcon)
                        Icon(
                          Icons.chevron_right,
                          color: Colors.grey[400],
                          size: 20,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BasicInfoSection extends StatelessWidget {
  final String mbti;
  final String major;
  final VoidCallback? onMbtiTap;
  final VoidCallback? onMajorTap;

  const _BasicInfoSection({
    required this.mbti,
    required this.major,
    this.onMbtiTap,
    this.onMajorTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '나에 대한 정보',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: _AppColors.textMain,
            ),
          ),
          const SizedBox(height: 12),
          const _BasicInfoItem(
            icon: Icons.nightlight_round,
            label: '별자리',
            value: '준비 중',
          ),
          const SizedBox(height: 8),
          _BasicInfoItem(
            icon: Icons.psychology,
            label: 'MBTI',
            value: mbti.isEmpty ? '아직 설정되지 않음' : mbti,
            onTap: onMbtiTap,
          ),
          const SizedBox(height: 8),
          _BasicInfoItem(
            icon: Icons.school,
            label: '전공',
            value: major.isEmpty ? '아직 설정되지 않음' : major,
            onTap: onMajorTap,
          ),
        ],
      ),
    );
  }
}

class _BasicInfoItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final VoidCallback? onTap;

  const _BasicInfoItem({
    required this.icon,
    required this.label,
    required this.value,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          color: _AppColors.placeholderBg,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(icon, color: Colors.grey[400], size: 20),
                const SizedBox(width: 12),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: _AppColors.textMain,
                  ),
                ),
              ],
            ),
            Row(
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 14,
                    color: _AppColors.textSub,
                  ),
                ),
                const SizedBox(width: 8),
                Icon(Icons.chevron_right, color: Colors.grey[400], size: 20),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
