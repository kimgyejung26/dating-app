// =============================================================================
// 채팅 목록 화면
// 경로: lib/features/chat/screens/chat_list_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const ChatListScreen()),
// );
// =============================================================================

import 'dart:ui';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../router/route_names.dart';
import '../models/chat_room_data.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF5A7E);
  static const Color textMain = Color(0xFF111111);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color gray500 = Color(0xFF6B7280);
  static const Color onlineGreen = Color(0xFF22C55E);
}

// =============================================================================
// 채팅 모델
// =============================================================================
class _ChatItem {
  final String id;
  final String name;
  final String avatarUrl;
  final String lastMessage;
  final String time;
  final bool isOnline;
  final bool hasUnread;
  final bool hasGradientBorder;
  final bool isGrayscale;

  const _ChatItem({
    required this.id,
    required this.name,
    required this.avatarUrl,
    required this.lastMessage,
    required this.time,
    this.isOnline = false,
    this.hasUnread = false,
    this.hasGradientBorder = false,
    this.isGrayscale = false,
  });
}

// =============================================================================
// 메인 화면
// =============================================================================
class ChatListScreen extends StatelessWidget {
  final VoidCallback? onFilter;
  final Function(String chatId)? onChatTap;
  final Function(int tabIndex)? onTabChange;
  final Function(int navIndex)? onNavTap;

  const ChatListScreen({
    super.key,
    this.onFilter,
    this.onChatTap,
    this.onTabChange,
    this.onNavTap,
  });

  static const List<_ChatItem> _chats = [
    _ChatItem(
      id: '1',
      name: '김지수',
      avatarUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBtt7Y2vSpmfeZkZz9MgWhu1gNFZz4EW0bZI4gS-x-Mz5CuOT5xQHNgU0Vi4PbzkGuzaBQtk7R-27MK-kukpLLD9mRT899HBUConFqkslrJW_YzCt8mvJrr6kgOhy-Rh5WRRWnstRxeBrsZe9hRihlFxYShp1cHsn6YGlcG810RH6oc04uEgm4lQ3brO0E0N16z0XtvjXOUEAiTBhrLp07VpCGlkhNbzGdnKO0AqpqEXv20rUI-mAomZzZhfDi8j9BBM4GMj1CikI25',
      lastMessage: '오늘 저녁에 시간 어때요? 강남역 근처에 맛있는 파스타집 알아요!',
      time: '방금 전',
      isOnline: true,
      hasUnread: true,
    ),
    _ChatItem(
      id: '2',
      name: '박민준',
      avatarUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDT0RK8vCMZ1fdHvltVWDurwmelCqxdies0jRqVZ_i25_eXkBCWJSMVbt1RHAXD45KRadkUNxR_I2QrUqowUVd6LAmnoRziNg9prWLp5-enwv4B2WnmBUopjrYkYLJ8Cfg4V19xvQCLCy3YiL3OWgiSdunOve4HFVg5cw_LyBCbsjMVnDX5loPDI6HE6DZspiFsBGHimsJGffCUK-K7s0tzpMe7fprq9qO_3oB0dJd_PqSGgr3Iu-txc3QGpFn_AS4QNEI9m3BKCzum',
      lastMessage: '반가워요! 프로필 사진 분위기가 정말 좋으시네요 ㅎㅎ',
      time: '10분 전',
      hasUnread: true,
      hasGradientBorder: true,
    ),
    _ChatItem(
      id: '3',
      name: '이서연',
      avatarUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCaoLaT2eg0Mr_CWMHTb5DFnC5NtnwIvbYSr7QlFAo429bhcRjjwZ9eM3KXCGGry_-VwTlGW47t69Ak613q9yN48tItC8XhxXVqQ86xWtAwYvjMYdr_P9OK5iF8KAOItKthh-1k1Yyb8Hw9Xsg0sNvpr2Lk-jPDZV8ycVaam8IOELv_NnjuKvJTEjGQ4_0BXIEfDkJW9k_eUdW51hXHAqnnL2vhABTODCwEnScNf9OS2fWATu403bThgZNQPrpzISgd7fJTNXMop1Xu',
      lastMessage: '네 알겠습니다~ 그럼 주말에 뵙는 걸로 할게요!',
      time: '1시간 전',
    ),
    _ChatItem(
      id: '4',
      name: '최현우',
      avatarUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBkclIYukugmfdmt_FqHn8n6ngOFy_HcntISLBJEEeng4mqga5wP8CTpo5nSbBLPrfKTmN1Cn5J65q8775JhJgm1JgGcKCUWg4SOouC6CFrYgDZxNGA2zgHwl5QWNh_gHj6N1Sq7I5YEeXtZ4oW4I12Sd21200BxMAniftmmGyNlkrjFtnR8ejLC3BdX7HJ8d2kvjG6mMxINka5PxHf-MuEX4QWFqSihtVj8ap_6F8IRbkAMAFu0GIa_J-0voPIWJoa2yTA138wQo28',
      lastMessage: '사진 보내드렸습니다. 확인해주세요.',
      time: '어제',
      isGrayscale: true,
    ),
    _ChatItem(
      id: '5',
      name: '정하나',
      avatarUrl:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuD5daUKQ65R86r5mD6ge1Dbq2r2x9s6mfF64QKG-Ok03q5Bk0RKkYndnQPpn2_qabOdm5-c4EXRI0RcmvAMRcdizRxM_MdpXu6n29zGbZckSgCt-BkONB0jM-ABrBhZOSyiQCZF1u9d7ukDbTa1eRA1CW7xgYecLFR_MFTngH-H503o6iKizja6XfMSkR7958WwJEMQ9lQ1lZAyr0rIZAP4-gQOOnEFV1H0w8SADoT7BJvmFJa6q5CKX4NFUuEur0R27-wnqmopSJM1',
      lastMessage: '즐거운 하루 보내세요 :)',
      time: '어제',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: CupertinoColors.white,
      child: Stack(
        children: [
          // 메인 콘텐츠
          CustomScrollView(
            physics: const BouncingScrollPhysics(),
            slivers: [
              // 헤더
              SliverToBoxAdapter(child: _Header(onFilter: onFilter)),
              // 탭 바
              SliverToBoxAdapter(child: _TabBar(onTabChange: onTabChange)),
              // 채팅 리스트
              SliverPadding(
                padding: EdgeInsets.fromLTRB(24, 8, 24, bottomPadding + 120),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) => _ChatListItem(
                      chat: _chats[index],
                      onTap: () {
                        if (onChatTap != null) {
                          onChatTap!(_chats[index].id);
                        } else {
                          final chat = _chats[index];
                          Navigator.of(context, rootNavigator: true).pushNamed(
                            RouteNames.chatRoom,
                            arguments: ChatRoomData(
                              chatRoomId: chat.id,
                              partnerId: chat.id,
                              partnerName: chat.name,
                              partnerAvatarUrl: chat.avatarUrl,
                              lastMessage: chat.lastMessage,
                              lastMessageTime: chat.time,
                            ),
                          );
                        }
                      },
                    ),
                    childCount: _chats.length,
                  ),
                ),
              ),
            ],
          ),
          // 하단 그라데이션
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            height: 96,
            child: IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      CupertinoColors.white.withValues(alpha: 0),
                      CupertinoColors.white,
                    ],
                  ),
                ),
              ),
            ),
          ),
          // 하단 네비게이션
          Positioned(
            left: 24,
            right: 24,
            bottom: bottomPadding + 32,
            child: _BottomNavBar(onTap: onNavTap),
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
  final VoidCallback? onFilter;

  const _Header({this.onFilter});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              '채팅',
              style: TextStyle(
                fontFamily: '.SF Pro Display',
                fontSize: 28,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
                color: _AppColors.textMain,
              ),
            ),
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {
                HapticFeedback.lightImpact();
                onFilter?.call();
              },
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: CupertinoColors.black.withValues(alpha: 0.03),
                ),
                child: const Icon(
                  CupertinoIcons.slider_horizontal_3,
                  size: 24,
                  color: _AppColors.textMain,
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
// 탭 바
// =============================================================================
class _TabBar extends StatefulWidget {
  final Function(int tabIndex)? onTabChange;

  const _TabBar({this.onTabChange});

  @override
  State<_TabBar> createState() => _TabBarState();
}

class _TabBarState extends State<_TabBar> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: Row(
        children: [
          _TabChip(
            label: '1:1',
            isSelected: _selectedIndex == 0,
            onTap: () {
              setState(() => _selectedIndex = 0);
              widget.onTabChange?.call(0);
            },
          ),
          const SizedBox(width: 12),
          _TabChip(
            label: '3:3',
            isSelected: _selectedIndex == 1,
            onTap: () {
              setState(() => _selectedIndex = 1);
              widget.onTabChange?.call(1);
            },
          ),
          const SizedBox(width: 12),
          _TabChip(
            label: 'AI 어시스턴트',
            icon: CupertinoIcons.sparkles,
            isSelected: _selectedIndex == 2,
            onTap: () {
              setState(() => _selectedIndex = 2);
              widget.onTabChange?.call(2);
            },
          ),
        ],
      ),
    );
  }
}

class _TabChip extends StatelessWidget {
  final String label;
  final IconData? icon;
  final bool isSelected;
  final VoidCallback? onTap;

  const _TabChip({
    required this.label,
    this.icon,
    this.isSelected = false,
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
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? _AppColors.primary : _AppColors.gray100,
          borderRadius: BorderRadius.circular(20),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: _AppColors.primary.withValues(alpha: 0.15),
                    blurRadius: 20,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 14,
                color: isSelected ? CupertinoColors.white : _AppColors.gray500,
              ),
              const SizedBox(width: 6),
            ],
            Text(
              label,
              style: TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: isSelected ? CupertinoColors.white : _AppColors.gray500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 채팅 리스트 아이템
// =============================================================================
class _ChatListItem extends StatelessWidget {
  final _ChatItem chat;
  final VoidCallback? onTap;

  const _ChatListItem({required this.chat, this.onTap});

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: EdgeInsets.zero,
      onPressed: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          children: [
            // 아바타
            _Avatar(
              imageUrl: chat.avatarUrl,
              isOnline: chat.isOnline,
              hasGradientBorder: chat.hasGradientBorder,
              isGrayscale: chat.isGrayscale,
            ),
            const SizedBox(width: 16),
            // 정보
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        chat.name,
                        style: TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 15,
                          fontWeight: chat.hasUnread
                              ? FontWeight.w700
                              : FontWeight.w600,
                          letterSpacing: -0.2,
                          color: _AppColors.textMain,
                        ),
                      ),
                      Text(
                        chat.time,
                        style: TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: _AppColors.gray400,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          chat.lastMessage,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontFamily: '.SF Pro Text',
                            fontSize: 13,
                            fontWeight: chat.hasUnread
                                ? FontWeight.w500
                                : FontWeight.w400,
                            color: chat.hasUnread
                                ? _AppColors.textMain
                                : _AppColors.gray500,
                            height: 1.3,
                          ),
                        ),
                      ),
                      if (chat.hasUnread) ...[
                        const SizedBox(width: 8),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: _AppColors.primary,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: _AppColors.primary.withValues(
                                  alpha: 0.3,
                                ),
                                blurRadius: 4,
                              ),
                            ],
                          ),
                        ),
                      ],
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

// =============================================================================
// 아바타
// =============================================================================
class _Avatar extends StatelessWidget {
  final String imageUrl;
  final bool isOnline;
  final bool hasGradientBorder;
  final bool isGrayscale;

  const _Avatar({
    required this.imageUrl,
    this.isOnline = false,
    this.hasGradientBorder = false,
    this.isGrayscale = false,
  });

  @override
  Widget build(BuildContext context) {
    Widget avatar = Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: _AppColors.gray100),
      ),
      clipBehavior: Clip.antiAlias,
      child: isGrayscale
          ? ColorFiltered(
              colorFilter: const ColorFilter.mode(
                CupertinoColors.systemGrey,
                BlendMode.saturation,
              ),
              child: Image.network(imageUrl, fit: BoxFit.cover),
            )
          : Image.network(imageUrl, fit: BoxFit.cover),
    );

    if (hasGradientBorder) {
      avatar = Container(
        padding: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topRight,
            end: Alignment.bottomLeft,
            colors: [Color(0xFFFACC15), Color(0xFFFF5A7E), Color(0xFFA855F7)],
          ),
        ),
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: CupertinoColors.white, width: 2),
          ),
          clipBehavior: Clip.antiAlias,
          child: Image.network(imageUrl, fit: BoxFit.cover),
        ),
      );
    }

    return Stack(
      children: [
        avatar,
        if (isOnline)
          Positioned(
            bottom: 2,
            right: 2,
            child: Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: _AppColors.onlineGreen,
                shape: BoxShape.circle,
                border: Border.all(color: CupertinoColors.white, width: 2),
              ),
            ),
          ),
      ],
    );
  }
}

// =============================================================================
// 하단 네비게이션
// =============================================================================
class _BottomNavBar extends StatelessWidget {
  final Function(int index)? onTap;

  const _BottomNavBar({this.onTap});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(32),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          decoration: BoxDecoration(
            color: CupertinoColors.white.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(
              color: CupertinoColors.white.withValues(alpha: 0.4),
            ),
            boxShadow: [
              BoxShadow(
                color: CupertinoColors.black.withValues(alpha: 0.15),
                blurRadius: 40,
                offset: const Offset(0, 10),
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
                icon: CupertinoIcons.chat_bubble_fill,
                label: '채팅',
                isActive: true,
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
              fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
              letterSpacing: -0.2,
              color: isActive ? _AppColors.primary : _AppColors.gray400,
            ),
          ),
        ],
      ),
    );
  }
}
