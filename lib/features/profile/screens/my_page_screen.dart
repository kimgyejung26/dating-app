// =============================================================================
// 내 페이지 화면
// 경로: lib/features/profile/screens/my_page_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const MyPageScreen()),
// );
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'dart:ui';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF0428B);
  static const Color backgroundLight = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFF9F9F9);
  static const Color textMain = Color(0xFF1A1A1A);
  static const Color textSub = Color(0xFF8E8E93);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray200 = Color(0xFFE5E7EB);
  static const Color gray300 = Color(0xFFD1D5DB);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color gray800 = Color(0xFF1F2937);
  static const Color pink50 = Color(0xFFFDF2F8);
  static const Color purple50 = Color(0xFFFAF5FF);
  static const Color purple500 = Color(0xFF8B5CF6);
  static const Color emerald50 = Color(0xFFECFDF5);
  static const Color emerald500 = Color(0xFF10B981);
}

// =============================================================================
// 메인 화면
// =============================================================================
class MyPageScreen extends StatelessWidget {
  final String userName;
  final String nickname;
  final String? avatarUrl;
  final int receivedHearts;
  final int friendsCount;
  final VoidCallback? onSettings;
  final VoidCallback? onEditAvatar;
  final VoidCallback? onEditProfile;
  final VoidCallback? onRecharge;
  final VoidCallback? onInviteFriends;
  final VoidCallback? onLogout;
  final Function(int index)? onNavTap;

  const MyPageScreen({
    super.key,
    this.userName = '사용자 이름',
    this.nickname = '닉네임',
    this.avatarUrl,
    this.receivedHearts = 128,
    this.friendsCount = 42,
    this.onSettings,
    this.onEditAvatar,
    this.onEditProfile,
    this.onRecharge,
    this.onInviteFriends,
    this.onLogout,
    this.onNavTap,
  });

  static const String _defaultAvatarUrl =
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAlamN6vna7onuxl6KAi_ZQF4inDOBV3szCSXLpbhKJBNMkA0GXEDwrk5twXPOs4LXS0G6ll7xVVnOu1xZIw3T23aOT20DZSwGXtD9KIye2kWfMoFNzq5XlSx8ubmnLS6wjbHBO_4uLkcv1ZGtJsN4_0SNfDo3apAeahRCJaJrzcoXrOl2m4mBTntOfUhvYG_8NcfWaWWb6x_3H0pxtW_aiZouvzrVG0P3gcL7VaYRfb2ifME_bMeHZSrJbaMnA3yGCgQH5eufdWC1f';

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.surface,
      child: Stack(
        children: [
          // 메인 콘텐츠
          CustomScrollView(
            physics: const BouncingScrollPhysics(),
            slivers: [
              // 헤더
              SliverToBoxAdapter(
                child: _Header(
                  onSettings:
                      onSettings ??
                      () => Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushNamed(RouteNames.settings),
                ),
              ),
              // 프로필 카드
              SliverToBoxAdapter(
                child: _ProfileCard(
                  userName: userName,
                  nickname: nickname,
                  avatarUrl: avatarUrl ?? _defaultAvatarUrl,
                  receivedHearts: receivedHearts,
                  friendsCount: friendsCount,
                  onEditAvatar: onEditAvatar,
                  onReceivedHeartsTap: () => Navigator.of(
                    context,
                    rootNavigator: true,
                  ).pushNamed(RouteNames.receivedHearts),
                  onFriendsTap: () => Navigator.of(
                    context,
                    rootNavigator: true,
                  ).pushNamed(RouteNames.friendsList),
                ),
              ),
              // 메뉴 리스트
              SliverToBoxAdapter(
                child: _MenuList(
                  onEditProfile:
                      onEditProfile ??
                      () => Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushNamed(RouteNames.profileEdit),
                  onRecharge:
                      onRecharge ??
                      () => Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushNamed(RouteNames.heartCharge),
                  onInviteFriends:
                      onInviteFriends ??
                      () => Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushNamed(RouteNames.friendsList),
                ),
              ),
              // 로그아웃
              SliverToBoxAdapter(child: _LogoutButton(onLogout: onLogout)),
              // 하단 여백
              SliverToBoxAdapter(child: SizedBox(height: bottomPadding + 100)),
            ],
          ),
          // 하단 네비게이션
          Positioned(
            left: 24,
            right: 24,
            bottom: bottomPadding + 16,
            child: _FloatingNavBar(onTap: onNavTap),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final VoidCallback? onSettings;

  const _Header({this.onSettings});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
        decoration: BoxDecoration(
          color: _AppColors.backgroundLight.withValues(alpha: 0.8),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              '내 페이지',
              style: TextStyle(
                fontFamily: '.SF Pro Display',
                fontSize: 21,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.3,
                color: _AppColors.textMain,
              ),
            ),
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {
                HapticFeedback.lightImpact();
                onSettings?.call();
              },
              child: Container(
                width: 40,
                height: 40,
                decoration: const BoxDecoration(shape: BoxShape.circle),
                child: const Icon(
                  CupertinoIcons.gear,
                  size: 24,
                  color: _AppColors.gray800,
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
// 프로필 카드
// =============================================================================
class _ProfileCard extends StatelessWidget {
  final String userName;
  final String nickname;
  final String avatarUrl;
  final int receivedHearts;
  final int friendsCount;
  final VoidCallback? onEditAvatar;
  final VoidCallback? onReceivedHeartsTap;
  final VoidCallback? onFriendsTap;

  const _ProfileCard({
    required this.userName,
    required this.nickname,
    required this.avatarUrl,
    required this.receivedHearts,
    required this.friendsCount,
    this.onEditAvatar,
    this.onReceivedHeartsTap,
    this.onFriendsTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.fromLTRB(0, 32, 0, 40),
      decoration: BoxDecoration(
        color: _AppColors.backgroundLight,
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(32),
          bottomRight: Radius.circular(32),
        ),
        boxShadow: [
          BoxShadow(
            color: CupertinoColors.black.withValues(alpha: 0.03),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Stack(
        children: [
          // 배경 그라데이션
          Positioned(
            top: -100,
            left: -50,
            right: -50,
            child: Container(
              height: 200,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    _AppColors.pink50.withValues(alpha: 0.5),
                    _AppColors.backgroundLight.withValues(alpha: 0),
                  ],
                ),
              ),
            ),
          ),
          // 콘텐츠
          Column(
            children: [
              // 아바타
              Stack(
                children: [
                  Container(
                    width: 128,
                    height: 128,
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const LinearGradient(
                        begin: Alignment.topRight,
                        end: Alignment.bottomLeft,
                        colors: [Color(0xFFFBCFE8), Color(0xFFE9D5FF)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: CupertinoColors.black.withValues(alpha: 0.05),
                          blurRadius: 40,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                        color: CupertinoColors.white,
                        shape: BoxShape.circle,
                      ),
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _AppColors.pink50,
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: Image.network(
                          avatarUrl,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => const Icon(
                            CupertinoIcons.person_fill,
                            size: 48,
                            color: _AppColors.gray400,
                          ),
                        ),
                      ),
                    ),
                  ),
                  // 편집 버튼
                  Positioned(
                    bottom: 4,
                    right: 4,
                    child: CupertinoButton(
                      padding: EdgeInsets.zero,
                      onPressed: onEditAvatar,
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: CupertinoColors.white,
                          shape: BoxShape.circle,
                          border: Border.all(color: _AppColors.gray100),
                          boxShadow: [
                            BoxShadow(
                              color: CupertinoColors.black.withValues(
                                alpha: 0.1,
                              ),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: const Icon(
                          CupertinoIcons.pencil,
                          size: 18,
                          color: _AppColors.gray400,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              // 이름 & 닉네임
              Text(
                userName,
                style: const TextStyle(
                  fontFamily: '.SF Pro Display',
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: _AppColors.textMain,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                nickname,
                style: const TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: _AppColors.textSub,
                ),
              ),
              const SizedBox(height: 24),
              // 통계 (받은 하트 / 친구 탭 시 해당 화면으로)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GestureDetector(
                    onTap: onReceivedHeartsTap,
                    child: _StatItem(label: '받은 하트', value: receivedHearts),
                  ),
                  Container(
                    width: 1,
                    height: 32,
                    margin: const EdgeInsets.symmetric(horizontal: 32),
                    color: _AppColors.gray200,
                  ),
                  GestureDetector(
                    onTap: onFriendsTap,
                    child: _StatItem(label: '친구', value: friendsCount),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final int value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          '$value',
          style: const TextStyle(
            fontFamily: '.SF Pro Display',
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: _AppColors.gray800,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontFamily: '.SF Pro Text',
            fontSize: 12,
            color: _AppColors.gray400,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 메뉴 리스트
// =============================================================================
class _MenuList extends StatelessWidget {
  final VoidCallback? onEditProfile;
  final VoidCallback? onRecharge;
  final VoidCallback? onInviteFriends;

  const _MenuList({this.onEditProfile, this.onRecharge, this.onInviteFriends});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: _AppColors.backgroundLight,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: CupertinoColors.black.withValues(alpha: 0.04),
              blurRadius: 12,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          children: [
            _MenuItem(
              icon: CupertinoIcons.person,
              iconBgColor: _AppColors.pink50,
              iconColor: _AppColors.primary,
              label: '프로필 편집',
              onTap: onEditProfile,
            ),
            Container(
              height: 1,
              color: _AppColors.gray100.withValues(alpha: 0.5),
            ),
            _MenuItem(
              icon: CupertinoIcons.creditcard,
              iconBgColor: _AppColors.purple50,
              iconColor: _AppColors.purple500,
              label: '머니 충전',
              onTap: onRecharge,
            ),
            Container(
              height: 1,
              color: _AppColors.gray100.withValues(alpha: 0.5),
            ),
            _MenuItem(
              icon: CupertinoIcons.person_add,
              iconBgColor: _AppColors.emerald50,
              iconColor: _AppColors.emerald500,
              label: '친구 초대',
              onTap: onInviteFriends,
            ),
          ],
        ),
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final Color iconBgColor;
  final Color iconColor;
  final String label;
  final VoidCallback? onTap;

  const _MenuItem({
    required this.icon,
    required this.iconBgColor,
    required this.iconColor,
    required this.label,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: () {
        HapticFeedback.selectionClick();
        onTap?.call();
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: iconBgColor,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 22, color: iconColor),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                label,
                style: const TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: _AppColors.gray800,
                ),
              ),
            ),
            const Icon(
              CupertinoIcons.chevron_right,
              size: 20,
              color: _AppColors.gray300,
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 로그아웃 버튼
// =============================================================================
class _LogoutButton extends StatelessWidget {
  final VoidCallback? onLogout;

  const _LogoutButton({this.onLogout});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Center(
        child: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: onLogout,
          child: const Text(
            '로그아웃',
            style: TextStyle(
              fontFamily: '.SF Pro Text',
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: _AppColors.gray400,
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// 플로팅 네비게이션
// =============================================================================
class _FloatingNavBar extends StatelessWidget {
  final Function(int index)? onTap;

  const _FloatingNavBar({this.onTap});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(32),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 24),
          decoration: BoxDecoration(
            color: CupertinoColors.white.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: _AppColors.gray100),
            boxShadow: [
              BoxShadow(
                color: CupertinoColors.black.withValues(alpha: 0.05),
                blurRadius: 20,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _NavItem(
                icon: CupertinoIcons.heart_fill,
                label: '설레연',
                onTap: () => onTap?.call(0),
              ),
              _NavItem(
                icon: CupertinoIcons.chat_bubble,
                label: '채팅',
                onTap: () => onTap?.call(1),
              ),
              _NavItem(
                icon: CupertinoIcons.calendar,
                label: '이벤트',
                onTap: () => onTap?.call(2),
              ),
              _NavItem(
                icon: CupertinoIcons.tree,
                label: '대나무숲',
                onTap: () => onTap?.call(3),
              ),
              _NavItem(
                icon: CupertinoIcons.person,
                label: '내 페이지',
                isActive: true,
                onTap: () => onTap?.call(4),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback? onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    this.isActive = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: onTap,
      child: SizedBox(
        width: 48,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 24,
              color: isActive ? _AppColors.primary : _AppColors.gray400,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 10,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                color: isActive ? _AppColors.primary : _AppColors.gray400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
