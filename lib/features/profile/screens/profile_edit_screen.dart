// =============================================================================
// 프로필 수정 화면
// 경로: lib/features/profile/screens/profile_edit_screen.dart
//
// HTML to Flutter 변환 구현
// - Cupertino 스타일 적용
// - 6매 사진 그리드 (메인 사진 강조)
// - 자기소개 텍스트 필드
// - 프로필 문답 및 상세 정보 입력 타일
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart' show Colors, Icons;

// =============================================================================
// 색상 정의
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF4B6E); // #FF4B6E
  static const Color backgroundLight = Color(0xFFF2F4F6); // #F2F4F6
  static const Color surfaceLight = CupertinoColors.white;
  static const Color textMain = Color(0xFF191F28); // #191F28
  static const Color textSub = Color(0xFF8B95A1); // #8B95A1
  static const Color placeholderBg = Color(0xFFF9FAFB); // gray-50
}

// =============================================================================
// 메인 화면
// =============================================================================
class ProfileEditScreen extends StatelessWidget {
  const ProfileEditScreen({super.key});

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
        child: Column(
          children: [
            // 수정하기 / 미리보기 탭
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

            // 메인 컨텐츠 영역
            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 24,
                ),
                child: Column(
                  children: const [
                    // 프로필 사진 섹션
                    _PhotoSection(),
                    SizedBox(height: 16),

                    // 자기소개 섹션
                    _SelfIntroSection(),
                    SizedBox(height: 16),

                    // 프로필 문답 섹션
                    _ProfileQuestionsSection(),
                    SizedBox(height: 16),

                    // 상세 정보 섹션 (관심사, 키 등)
                    _DetailInfoSection(),
                    SizedBox(height: 16),

                    // 나에 대한 정보 (별자리, MBTI)
                    _BasicInfoSection(),

                    SizedBox(height: 100), // 하단 여백
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

// =============================================================================
// 프로필 사진 섹션 (그리드)
// =============================================================================
class _PhotoSection extends StatelessWidget {
  const _PhotoSection();

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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
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
          // 그리드 형태 (커스텀 Row/Column 조합으로 구현)
          // Grid cols 3, gap 2
          LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;
              final gap = 8.0;
              final itemWidth = (width - gap * 2) / 3;

              return Column(
                children: [
                  // 첫 번째 줄 (메인 사진(2x2) + 작은 사진 2개) ??
                  // HTML: col-span-2 row-span-2 for main item
                  SizedBox(
                    height: itemWidth * 2 + gap,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // 메인 사진 (2 col x 2 row)
                        Expanded(
                          flex: 2,
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Image.network(
                                  'https://lh3.googleusercontent.com/aida-public/AB6AXuBo85pW-dts5CXtcdVonhUQTaZeu8Kfxlnf5IL-SGXzi-QRjuDx13wY-DJmsliAz2iJtFg64g2BlPSVyOt9eFsrAd8VVeUEpgWD1dHzNpfyxah9MfrXW6rTGqVQsH1m2IeeKqbj0Kl2Z3V4stCnd50o_pci5iuHddxStFmbNPp2EC8BZa7W0RlLyWbaPLF4tBtAZsewIEKvGOYD8oSfHEt719fHJfV79widveqf7Ce1m-VdlxrGfvQmH-kRyL-5NbHcn6BRT1wmA8lA',
                                  fit: BoxFit.cover,
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
                                    color: Colors.black.withValues(alpha: 0.6),
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
                        // 우측 열 (작은 사진 2개)
                        Expanded(
                          flex: 1,
                          child: Column(
                            children: [
                              Expanded(
                                child: _PhotoItem(
                                  imageUrl:
                                      'https://lh3.googleusercontent.com/aida-public/AB6AXuDDrhuShMcRRQfYdWk1Z3aq_wiCowDIltz_kWXUMZ97B9n9rBaxyRdyp0cdnUfLfvBZFvhxXq5qkfjspWr2AjUML7MibNKDtV4OZBNgBKLfHUBKJFLxJamLz57KA7s2721zIFi0g-KP8FU0vidA4wR7m8U-Iuxmb5wVnfAGzNX6HcR7fU9Eq0OljY3Lp34_B1Wn3o_F79hye9kLBX0WGufMzgfm1kzrjpjwL1qmcI0EusuWuqAga1a662rD2YRoQoOiyunK-hg4cCMD',
                                ),
                              ),
                              SizedBox(height: gap),
                              Expanded(
                                child: _PhotoItem(
                                  imageUrl:
                                      'https://lh3.googleusercontent.com/aida-public/AB6AXuCPYDTQKNHk3j3UWHIzrk3FGcrp73LJfPepxvZ3Ica862X7fs6TUQb41-XhDarRmQnkXEKwBCEKHREriMoULsMU9LPsuhytfiX3wE9Fihd7IowPSfaJgldxTqP739XcAxh4l2K4TXj_KVj03uZVd6zq8I84TVkBC3gU1rYe4jd-CUC5M4iknORtI1OMOdOdAChyHdew2wPKYURLEDPP2nkTJ9h-qCZL4GNA_nQlQfEjT-As4ZHU8gC92ptihL7Kb5cbFIOqVCqGgKm7',
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  SizedBox(height: gap),
                  // 두 번째 줄 (작은 사진 3개) - HTML 구조와 약간 다르게 해석될 수 있으나, 3xX 그리드로 보임
                  SizedBox(
                    height: itemWidth,
                    child: Row(
                      children: [
                        Expanded(
                          child: _PhotoItem(
                            imageUrl:
                                'https://lh3.googleusercontent.com/aida-public/AB6AXuDNZiKEeZDX1J5ifE6QhQp5JjYS0AlAWYXh2A5_3ksm7J11EVKsgHkRTMSLeey61X9ENyiO23W-xjYiqITmbXDT9OociSYsnbLF_YbDO1gTtb-xUa8SzexCSnQ9JPpwPwy2uw-V7ardp6K9sZiv-MgveloPmBJvqZuNrBCwHbZrlRRSB2TCHZ7JLVsSWc9jbxrRGAkA2Bmqr0hIKm2D-4NBGyzz7YAHYC9IGKriimOOyUyp408Sb4vuIn7w0j8hgmfahtLzwOrDPe-3',
                          ),
                        ),
                        SizedBox(width: gap),
                        const Expanded(child: _AddPhotoButton()),
                        SizedBox(width: gap),
                        const Expanded(child: _AddPhotoButton()),
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
                Icon(Icons.chevron_right, size: 16, color: _AppColors.primary),
              ],
            ),
          ),
        ],
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
        border: Border.all(
          color: const Color(0xFFE5E7EB),
          style:
              BorderStyle.solid, // Dashed unsupported natively in simple Border
          width: 2,
        ),
      ),
      child: const Icon(Icons.add_rounded, color: Color(0xFFD1D5DB), size: 32),
    );
  }
}

// =============================================================================
// 자기소개 섹션
// =============================================================================
class _SelfIntroSection extends StatelessWidget {
  const _SelfIntroSection();

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
                height: 128,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _AppColors.placeholderBg,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  '목소리가 좋다는 소리를 많이 들어요 저는 잘 모르겠지만 저랑 잘 맞는 분이었으면 좋겠어요',
                  style: TextStyle(
                    fontSize: 14,
                    height: 1.5,
                    color: _AppColors.textMain,
                  ),
                ),
              ),
              Positioned(
                bottom: 12,
                right: 12,
                child: const Text(
                  '451',
                  style: TextStyle(fontSize: 12, color: _AppColors.textSub),
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
    );
  }
}

// =============================================================================
// 프로필 문답 섹션
// =============================================================================
class _ProfileQuestionsSection extends StatelessWidget {
  const _ProfileQuestionsSection();

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
              border: Border.all(
                color: const Color(0xFFE5E7EB),
                style: BorderStyle.solid, // Dashed logic omitted for simplicity
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      '프로필 문답 선택하기',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: _AppColors.textMain,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      '프로필 문답 작성하기',
                      style: TextStyle(fontSize: 14, color: _AppColors.textSub),
                    ),
                  ],
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
    );
  }
}

// =============================================================================
// 상세 정보 섹션 (관심사, 키, 관계 등)
// =============================================================================
class _DetailInfoSection extends StatelessWidget {
  const _DetailInfoSection();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: const [
        _DetailTile(
          title: '관심사',
          content: '볼링, 요리, 노래방, 한강에서 치맥, 악기, 빈티지 쇼핑, 넷플릭스',
          showIcon: false,
        ),
        SizedBox(height: 16),
        _DetailTile(title: '키', content: '176 cm', icon: Icons.straighten),
        SizedBox(height: 16),
        _DetailTile(
          title: '내가 찾는 관계',
          content: '진지한 연애를 찾지만\n캐주얼해도 괜찮음',
          emoji: '😍',
          icon: Icons.visibility,
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

  const _DetailTile({
    required this.title,
    required this.content,
    this.icon,
    this.emoji,
    this.showIcon = true,
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
                      if (showIcon && icon == null && emoji == null) ...[
                        // No logic needed, just structural
                      ],
                      Expanded(
                        child: Text(
                          content,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: _AppColors.textMain,
                          ),
                          maxLines: 2,
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
    );
  }
}

// =============================================================================
// 기본 정보 섹션 (별자리, MBTI)
// =============================================================================
class _BasicInfoSection extends StatelessWidget {
  const _BasicInfoSection();

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
          _BasicInfoItem(
            icon: Icons.nightlight_round,
            label: '별자리',
            value: '염소자리',
          ),
          const SizedBox(height: 8),
          _BasicInfoItem(icon: Icons.psychology, label: 'MBTI', value: 'ENTP'),
        ],
      ),
    );
  }
}

class _BasicInfoItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _BasicInfoItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
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
                style: const TextStyle(fontSize: 14, color: _AppColors.textSub),
              ),
              const SizedBox(width: 8),
              Icon(Icons.chevron_right, color: Colors.grey[400], size: 20),
            ],
          ),
        ],
      ),
    );
  }
}
