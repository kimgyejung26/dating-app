// =============================================================================
// 커뮤니티(대나무숲) 메인 화면
// 경로: lib/features/community/screens/community_screen.dart
//
// 디자인: Glassmorphism 스타일, 꽃잎 배경, 카드형 피드
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui';
import 'dart:math' as math;
import '../../../router/route_names.dart';
import '../../../data/models/community/post_model.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF0428B);
  static const Color softPink = Color(0xFFFFE4E6);
  static const Color softLavender = Color(0xFFE9D5FF);

  static const Color textMain = Color(0xFF181114);
  static const Color textSub = Color(0xFF9CA3AF); // gray-400
  static const Color cardBg = Color(0xE6FFFFFF); // white/90
}

// =============================================================================
// 메인 화면
// =============================================================================
class CommunityScreen extends StatefulWidget {
  final Function(int index)? onNavTap;

  const CommunityScreen({super.key, this.onNavTap});

  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  final ScrollController _scrollController = ScrollController();
  String _selectedCategory = '전체';

  final List<String> _categories = ['전체', '인기', '설렘', '고민', '유머', '홍보'];

  // TODO: Firebase 연동 시 Firestore 쿼리로 교체
  final List<PostModel> _mockPosts = [
    PostModel(
      id: 'post_1',
      authorId: 'user_1',
      authorNickname: '익명의 여우',
      authorProfileUrl: null,
      category: '짝사랑',
      title: '',
      content: '어제 같이 마신 커피가 자꾸 생각나는데 이상한가요? 심장이 너무 빨리 뛰어서 잠도 거의 못 잤어요.. 💓',
      likeCount: 24,
      commentCount: 5,
      isLiked: false,
      createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
      updatedAt: DateTime.now().subtract(const Duration(minutes: 10)),
    ),
    PostModel(
      id: 'post_2',
      authorId: 'user_2',
      authorNickname: '설레는 하루',
      authorProfileUrl: null,
      category: '첫만남',
      title: '',
      content: '오늘 강남에서 앱으로 처음 만나는 분이 있어요. 너무 떨리는데 옷차림 괜찮을까요? 응원해주세요! 🌸',
      likeCount: 156,
      commentCount: 32,
      isLiked: true,
      createdAt: DateTime.now().subtract(const Duration(minutes: 35)),
      updatedAt: DateTime.now().subtract(const Duration(minutes: 35)),
    ),
    PostModel(
      id: 'post_3',
      authorId: 'user_3',
      authorNickname: '고민많은 곰',
      authorProfileUrl: null,
      category: '고민',
      title: '',
      content: '먼저 연락하고 싶은데 너무 매달리는 것처럼 보일까 봐 걱정돼요. 연애는 왜 이렇게 어려운 걸까요? 🥲',
      likeCount: 12,
      commentCount: 15,
      isLiked: false,
      createdAt: DateTime.now().subtract(const Duration(hours: 1)),
      updatedAt: DateTime.now().subtract(const Duration(hours: 1)),
    ),
    PostModel(
      id: 'post_4',
      authorId: 'user_4',
      authorNickname: '웃긴 펭귄',
      authorProfileUrl: null,
      category: '유머',
      title: '',
      content:
          '소개팅 나갔는데 상대방이 전 애인 얘기를 30분 동안 함... 이거 도망가라는 신호 맞죠? ㅋㅋㅋ 🏃\u200d♂️',
      likeCount: 89,
      commentCount: 45,
      isLiked: false,
      createdAt: DateTime.now().subtract(const Duration(hours: 3)),
      updatedAt: DateTime.now().subtract(const Duration(hours: 3)),
    ),
  ];

  /// 카테고리별 배경색 매핑
  Color _getCategoryColor(String category) {
    switch (category) {
      case '짝사랑':
        return const Color(0xFFFDE8F3);
      case '첫만남':
        return const Color(0xFFF3E8FF);
      case '고민':
        return const Color(0xFFF3F4F6);
      case '유머':
        return const Color(0xFFFEF3C7);
      case '설렘':
        return const Color(0xFFFCE7F3);
      default:
        return const Color(0xFFF3F4F6);
    }
  }

  /// 카테고리별 텍스트색 매핑
  Color _getCategoryTextColor(String category) {
    switch (category) {
      case '짝사랑':
        return const Color(0xFFDB2777);
      case '첫만남':
        return const Color(0xFF9333EA);
      case '고민':
        return const Color(0xFF4B5563);
      case '유머':
        return const Color(0xFFD97706);
      case '설렘':
        return const Color(0xFFEC4899);
      default:
        return const Color(0xFF4B5563);
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    // 배경 그라데이션: soft-pink -> white -> soft-lavender
    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        children: [
          // 1. 배경 (Gradient & Petals)
          const _BackgroundDecoration(),

          // 2. 메인 컨텐츠
          SafeArea(
            bottom: false,
            child: NestedScrollView(
              headerSliverBuilder: (context, innerBoxIsScrolled) {
                return [
                  // 상단 앱바 & 칩 (Sticky 효과를 위해 Sliver 사용)
                  SliverPersistentHeader(
                    pinned: true,
                    delegate: _StickyHeaderDelegate(
                      minHeight: 110, // TopBar(50) + Chips(50) + padding
                      maxHeight: 110,
                      child: _HeaderArea(
                        selectedCategory: _selectedCategory,
                        categories: _categories,
                        onCategorySelected: (category) {
                          HapticFeedback.selectionClick();
                          setState(() => _selectedCategory = category);
                        },
                      ),
                    ),
                  ),
                ];
              },
              body: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
                physics: const BouncingScrollPhysics(),
                children: [
                  // 게시글 카드 목록 (mock 데이터 기반)
                  for (int i = 0; i < _mockPosts.length; i++) ...[
                    _PostCard(
                      post: _mockPosts[i],
                      categoryColor: _getCategoryColor(_mockPosts[i].category),
                      categoryTextColor: _getCategoryTextColor(
                        _mockPosts[i].category,
                      ),
                    ),
                    if (i < _mockPosts.length - 1) const SizedBox(height: 16),
                    // 이미지 카드를 2번째 게시글 뒤에 삽입
                    if (i == 1) ...[
                      const SizedBox(height: 16),
                      const _ImageCard(
                        badge: '오늘의 추천',
                        title: '벚꽃 시즌을 위한 완벽한 데이트 장소 🌸',
                        author: '관리자',
                        time: '2시간 전',
                        imageUrl:
                            'https://images.unsplash.com/photo-1522383225653-ed111181a951?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80',
                      ),
                      const SizedBox(height: 16),
                    ],
                  ],
                ],
              ),
            ),
          ),

          // 3. 하단 네비게이션
          Positioned(
            left: 24,
            right: 24,
            bottom: bottomPadding + 32,
            child: _BottomNavBar(onTap: widget.onNavTap),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 배경 장식 (Gradient & 꽃잎)
// =============================================================================
class _BackgroundDecoration extends StatelessWidget {
  const _BackgroundDecoration();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Gradient Background
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                _AppColors.softPink,
                Colors.white,
                _AppColors.softLavender,
              ],
            ),
          ),
        ),
        // Floating Petals (Icons with rotation/opacity)
        Positioned(
          top: 80,
          left: 40,
          child: _PetalIcon(
            size: 32,
            color: _AppColors.primary.withValues(alpha: 0.2),
            rotation: 45,
          ),
        ),
        Positioned(
          top: 160,
          right: 48,
          child: _PetalIcon(
            size: 48,
            color: _AppColors.primary.withValues(alpha: 0.1),
            rotation: -12,
          ),
        ),
        Positioned(
          bottom: 120,
          left: 32,
          child: _PetalIcon(
            size: 24,
            color: _AppColors.primary.withValues(alpha: 0.15),
            rotation: 90,
          ),
        ),
        Positioned(
          bottom: 240,
          right: 24,
          child: _PetalIcon(
            size: 40,
            color: _AppColors.primary.withValues(alpha: 0.1),
            rotation: 180,
          ),
        ),
      ],
    );
  }
}

class _PetalIcon extends StatelessWidget {
  final double size;
  final Color color;
  final double rotation;

  const _PetalIcon({
    required this.size,
    required this.color,
    required this.rotation,
  });

  @override
  Widget build(BuildContext context) {
    return Transform.rotate(
      angle: rotation * math.pi / 180,
      child: Icon(
        CupertinoIcons.drop_fill, // 꽃잎 모양과 유사한 아이콘 활용 (혹은 heart_fill 등)
        size: size,
        color: color,
      ),
    );
  }
}

// =============================================================================
// 헤더 영역 (TopBar + Chips)
// =============================================================================
class _HeaderArea extends StatelessWidget {
  final String selectedCategory;
  final List<String> categories;
  final Function(String) onCategorySelected;

  const _HeaderArea({
    required this.selectedCategory,
    required this.categories,
    required this.onCategorySelected,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          color: Colors.white.withValues(alpha: 0.7),
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              // 1. Top Bar
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                child: Row(
                  children: [
                    _CircleIconButton(
                      icon: Icons.menu,
                      onTap: () {},
                      color: Colors.black,
                    ),
                    const Expanded(
                      child: Text(
                        '대나무숲',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontFamily: 'Noto Sans KR',
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                          color: _AppColors.textMain,
                        ),
                      ),
                    ),
                    _CircleIconButton(
                      icon: Icons.edit_outlined,
                      onTap: () {
                        Navigator.of(context, rootNavigator: true).pushNamed(RouteNames.postWrite);
                      },
                      color: _AppColors.primary,
                      backgroundColor: _AppColors.primary.withValues(
                        alpha: 0.1,
                      ),
                    ),
                  ],
                ),
              ),
              // 2. Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                physics: const BouncingScrollPhysics(),
                child: Row(
                  children: categories.map((category) {
                    final bool isSelected = selectedCategory == category;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: GestureDetector(
                        onTap: () => onCategorySelected(category),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? _AppColors.textMain
                                : Colors.white.withValues(alpha: 0.8),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isSelected
                                  ? Colors.transparent
                                  : Colors.white,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: isSelected
                                    ? Colors.black.withValues(alpha: 0.2)
                                    : Colors.black.withValues(alpha: 0.05),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Text(
                            category,
                            style: TextStyle(
                              fontFamily: 'Plus Jakarta Sans',
                              fontSize: 14,
                              fontWeight: isSelected
                                  ? FontWeight.w600
                                  : FontWeight.w500,
                              color: isSelected
                                  ? Colors.white
                                  : _AppColors.textMain,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CircleIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final Color color;
  final Color? backgroundColor;

  const _CircleIconButton({
    required this.icon,
    required this.onTap,
    required this.color,
    this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: backgroundColor ?? Colors.transparent, // hover 효과는 생략
        ),
        child: Icon(icon, color: color, size: 22),
      ),
    );
  }
}

// =============================================================================
// Sticky Header Delegate
// =============================================================================
class _StickyHeaderDelegate extends SliverPersistentHeaderDelegate {
  final double minHeight;
  final double maxHeight;
  final Widget child;

  _StickyHeaderDelegate({
    required this.minHeight,
    required this.maxHeight,
    required this.child,
  });

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return SizedBox.expand(child: child);
  }

  @override
  double get maxExtent => maxHeight;

  @override
  double get minExtent => minHeight;

  @override
  bool shouldRebuild(_StickyHeaderDelegate oldDelegate) {
    return maxHeight != oldDelegate.maxHeight ||
        minHeight != oldDelegate.minHeight ||
        child != oldDelegate.child;
  }
}

// =============================================================================
// 시간 포맷 헬퍼
// =============================================================================
String _formatTimeAgo(DateTime dateTime) {
  final diff = DateTime.now().difference(dateTime);
  if (diff.inMinutes < 1) return '방금 전';
  if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
  if (diff.inHours < 24) return '${diff.inHours}시간 전';
  if (diff.inDays < 7) return '${diff.inDays}일 전';
  return '${dateTime.month}/${dateTime.day}';
}

// =============================================================================
// 게시글 카드
// =============================================================================
class _PostCard extends StatelessWidget {
  final PostModel post;
  final Color categoryColor;
  final Color categoryTextColor;

  const _PostCard({
    required this.post,
    required this.categoryColor,
    required this.categoryTextColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        Navigator.of(
          context,
          rootNavigator: true,
        ).pushNamed(RouteNames.postDetail, arguments: post);
      },
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: _AppColors.cardBg, // Glassmorphism 느낌
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: _AppColors.primary.withValues(alpha: 0.05),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: categoryColor,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        post.category,
                        style: TextStyle(
                          fontFamily: 'Noto Sans KR',
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: categoryTextColor,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _formatTimeAgo(post.createdAt),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: _AppColors.textSub,
                      ),
                    ),
                  ],
                ),
                Icon(Icons.more_horiz, color: Colors.grey[300]),
              ],
            ),
            const SizedBox(height: 16),
            // Content
            Text(
              post.content,
              style: const TextStyle(
                fontSize: 16,
                height: 1.6,
                fontWeight: FontWeight.w500,
                color: _AppColors.textMain,
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 16),
            // Divider
            Divider(color: Colors.grey[100], height: 1),
            const SizedBox(height: 12),
            // Footer
            Row(
              children: [
                _ActionIcon(
                  icon: post.isLiked
                      ? Icons.favorite
                      : Icons.favorite_border_rounded,
                  count: post.likeCount,
                  color: post.isLiked ? _AppColors.primary : Colors.grey[400]!,
                  activeColor: _AppColors.primary,
                ),
                const SizedBox(width: 20),
                _ActionIcon(
                  icon: Icons.chat_bubble_outline_rounded,
                  count: post.commentCount,
                  color: Colors.grey[400]!,
                  activeColor: Colors.blue,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionIcon extends StatelessWidget {
  final IconData icon;
  final int count;
  final Color color;
  final Color activeColor;

  const _ActionIcon({
    required this.icon,
    required this.count,
    required this.color,
    required this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(width: 4),
        Text(
          '$count',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: color == activeColor ? activeColor : Colors.grey[500],
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 이미지 카드
// =============================================================================
class _ImageCard extends StatelessWidget {
  final String badge;
  final String title;
  final String author;
  final String time;
  final String imageUrl;

  const _ImageCard({
    required this.badge,
    required this.title,
    required this.author,
    required this.time,
    required this.imageUrl,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 250,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: [
            // Image
            Positioned.fill(
              child: Image.network(
                imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  color: Colors.grey[300],
                  child: const Center(
                    child: Icon(Icons.image_not_supported, color: Colors.grey),
                  ),
                ),
              ),
            ),
            // Gradient Overlay
            Positioned.fill(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withValues(alpha: 0.8),
                    ],
                    stops: const [0.5, 1.0],
                  ),
                ),
              ),
            ),
            // Content
            Positioned(
              left: 20,
              right: 20,
              bottom: 20,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.2),
                      ),
                    ),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 4, sigmaY: 4),
                      child: Text(
                        '[$badge]',
                        style: const TextStyle(
                          fontFamily: 'Noto Sans KR',
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '$author • $time',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withValues(alpha: 0.8),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'Read More',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
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
            color: Colors.white.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: Colors.white.withValues(alpha: 0.4)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.15),
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
                isActive: true,
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
            color: isActive ? _AppColors.primary : const Color(0xFF9CA3AF),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontFamily: '.SF Pro Text',
              fontSize: 10,
              fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
              letterSpacing: -0.2,
              color: isActive ? _AppColors.primary : const Color(0xFF9CA3AF),
            ),
          ),
        ],
      ),
    );
  }
}
