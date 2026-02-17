// =============================================================================
// 대나무숲(커뮤니티) 게시글 상세 화면
// 경로: lib/features/community/screens/post_detail_screen.dart
//
// 디자인: Glassmorphism 헤더/입력창, 그라데이션 배경, 댓글 리스트
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui';
import '../../../data/models/community/post_model.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFF0428B);
  static const Color backgroundLight = Color(0xFFF8F6F7);
  // Theme colors based on HTML example
  static const Color gradientStart = Color(0xFFFFF0F5);
  static const Color gradientMiddle = Color(0xFFF3E5F5);
  static const Color gradientEnd = Color(0xFFE1BEE7);

  static const Color textMain = Color(0xFF1E293B); // slate-800
  static const Color textBody = Color(0xFF334155); // slate-700
  static const Color textSub = Color(0xFF94A3B8); // slate-400
}

// =============================================================================
// 메인 화면
// =============================================================================
class PostDetailScreen extends StatefulWidget {
  final PostModel? post;

  const PostDetailScreen({super.key, this.post});

  @override
  State<PostDetailScreen> createState() => _PostDetailScreenState();
}

class _PostDetailScreenState extends State<PostDetailScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _commentController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  late AnimationController _animationController;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _commentController.dispose();
    _scrollController.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: Stack(
        children: [
          // 1. 배경 (Gradient & Animated Blobs)
          const _BackgroundDecoration(),

          // 2. 메인 컨텐츠
          SafeArea(
            child: Column(
              children: [
                // 헤더
                _Header(onBack: () => Navigator.of(context).pop()),

                // 스크롤 영역 (게시글 + 댓글)
                Expanded(
                  child: ListView(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(
                      20,
                      0,
                      20,
                      100,
                    ), // Bottom padding for input bar
                    physics: const BouncingScrollPhysics(),
                    children: [
                      const SizedBox(height: 16),
                      // 게시글 본문 카드
                      _ConfessionCard(post: widget.post),

                      const SizedBox(height: 32),

                      // 댓글 섹션 헤더
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'COMMENTS',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: _AppColors.textMain.withValues(alpha: 0.8),
                              letterSpacing: 1.2,
                            ),
                          ),
                          Text(
                            'Recent first',
                            style: TextStyle(
                              fontSize: 12,
                              color: _AppColors.textSub,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 댓글 리스트
                      const _CommentList(),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // 3. 하단 입력 바 (Sticky Bottom)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _BottomInputBar(controller: _commentController),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 배경 장식
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
                _AppColors.gradientStart,
                _AppColors.gradientMiddle,
                _AppColors.gradientEnd,
              ],
            ),
          ),
        ),

        // Blobs (Positioned fixed for simplicity, can be animated)
        Positioned(
          top: -100,
          left: -100,
          child: Container(
            width: 300,
            height: 300,
            decoration: BoxDecoration(
              color: Colors.pink.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),
        Positioned(
          bottom: 100,
          right: -50,
          child: Container(
            width: 250,
            height: 250,
            decoration: BoxDecoration(
              color: Colors.purple.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
              child: Container(color: Colors.transparent),
            ),
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final VoidCallback onBack;

  const _Header({required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _GlassIconButton(
            icon: Icons.arrow_back_ios_new_rounded,
            onTap: onBack,
          ),
          const Text(
            'Confession',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _AppColors.textMain,
            ),
          ),
          _GlassIconButton(icon: Icons.more_horiz_rounded, onTap: () {}),
        ],
      ),
    );
  }
}

class _GlassIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _GlassIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: ClipOval(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            width: 40,
            height: 40,
            color: Colors.white.withValues(alpha: 0.3),
            child: Icon(icon, color: _AppColors.textMain, size: 20),
          ),
        ),
      ),
    );
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
// 게시글 본문 카드
// =============================================================================
class _ConfessionCard extends StatelessWidget {
  final PostModel? post;

  const _ConfessionCard({this.post});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: _AppColors.primary.withValues(alpha: 0.15),
            blurRadius: 40,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Column(
          children: [
            // Top Decoration Gradient Line
            Container(
              height: 4,
              width: double.infinity,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.pink.shade300,
                    _AppColors.primary,
                    Colors.purple.shade300,
                  ],
                ),
              ),
            ),

            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // User Info
                  Row(
                    children: [
                      Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          image: const DecorationImage(
                            image: NetworkImage(
                              'https://lh3.googleusercontent.com/aida-public/AB6AXuBk0o_GmNHLyMyPcY2Y54ctiPHrUNlWFgNTqligfhZS3eauKQHgr8kuZLkCvA2SwbSYzGA-m88TUgz8UMugDNINFX4Ya16U-4SQTX4C9Av6C0JZhBXPjjGNYe-lAbVyEumZIjHiwC8CuBPcwgqySC8DvadEnVIGSjrJ3hLy7rEwflpIUHheIBGTjL_sLVp7FBEBSyg8YIOVpYkUuuwWUnx64kNAhId3wvGEA8Mvmt_v6szjmMGXqr8GIU--pE9UNJsHpj-Ixam5eekG',
                            ),
                            fit: BoxFit.cover,
                          ),
                          border: Border.all(
                            color: Colors.pink.shade100,
                            width: 2,
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '익명의 여우',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: _AppColors.textMain,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            post != null
                                ? _formatTimeAgo(post!.createdAt)
                                : '2시간 전',
                            style: TextStyle(
                              fontSize: 12,
                              color: _AppColors.textSub,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),

                  const SizedBox(height: 24),

                  // Tags
                  Row(
                    children: [
                      _Tag(
                        emoji: '🌸',
                        label: '#짝사랑',
                        color: Colors.pink,
                        bgColor: Colors.pink.shade50,
                        borderColor: Colors.pink.shade100,
                      ),
                      const SizedBox(width: 8),
                      _Tag(
                        emoji: '💓',
                        label: '#설렘주의',
                        color: Colors.purple,
                        bgColor: Colors.purple.shade50,
                        borderColor: Colors.purple.shade100,
                      ),
                    ],
                  ),

                  const SizedBox(height: 24),

                  // Content
                  Text(
                    post?.content ??
                        '오늘 또 도서관에서 그쪽 봤어요. 베이지색 니트 입고 계셨는데 너무 포근해 보였어요.\n\n인사라도 건네고 싶었는데, 무슨 책 읽냐고 물어보고 싶었는데... 용기가 안 나더라고요. 심장이 너무 쿵쾅거려서 다 들릴까 봐 조마조마했어요.\n\n다음엔 꼭 용기 내볼게요. 그때까진 책 뒤에서 몰래 지켜만 볼게요.',
                    style: const TextStyle(
                      fontSize: 16,
                      height: 1.6,
                      color: _AppColors.textBody,
                    ),
                  ),

                  const SizedBox(height: 24),
                  Divider(height: 1, color: Colors.grey.shade100),
                  const SizedBox(height: 16),

                  // Actions
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          _ActionButton(
                            icon: Icons.favorite_rounded,
                            label: '${post?.likeCount ?? 124}',
                            color: _AppColors.primary,
                            isFilled: post?.isLiked ?? true,
                          ),
                          const SizedBox(width: 20),
                          _ActionButton(
                            icon: Icons.chat_bubble_outline_rounded,
                            label: '${post?.commentCount ?? 15}',
                            color: _AppColors.textSub,
                            isFilled: false,
                          ),
                        ],
                      ),
                      Icon(Icons.ios_share_rounded, color: _AppColors.textSub),
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

class _Tag extends StatelessWidget {
  final String emoji;
  final String label;
  final Color color;
  final Color bgColor;
  final Color borderColor;

  const _Tag({
    required this.emoji,
    required this.label,
    required this.color,
    required this.bgColor,
    required this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool isFilled;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.isFilled,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: isFilled ? color : Colors.grey.shade400, size: 22),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: isFilled ? Colors.grey.shade600 : Colors.grey.shade500,
          ),
        ),
      ],
    );
  }
}

// =============================================================================
// 댓글 리스트
// =============================================================================
class _CommentList extends StatelessWidget {
  const _CommentList();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: const [
        _CommentItem(
          author: '파란 토끼',
          time: '10분 전',
          content: '힘내세요! 다음엔 꼭 성공하실 거예요. 가볍게 "안녕하세요"부터 시작해보세요 👋',
          avatarUrl:
              'https://lh3.googleusercontent.com/aida-public/AB6AXuAzzvkyaDRR5Q3RnVDmdX6xq2jOzxX4vep_IhDVuuHJwIepTZg263zHlyQrJNC0fvT6xxiJcRnaWSvPsHbzFvflvewXWU_kuEpW3Tjo2B1c11679fGgzpXCCxTGaJWEeHeb2YGmwFSKOVkcMwtnsooqo3_N3m2wXB3nidieKDNt_YAdRIBVec7HAOPKTIK9txicy2fuab8To5a5ZFpHDN7nr19RtKR2MHgxA039DUc0xtqrqTidyF5clCUT2YHAGg1TKbBLjoEE5KnS',
          likeCount: 0,
        ),
        SizedBox(height: 16),
        _CommentItem(
          author: '졸린 부엉이',
          time: '45분 전',
          content: '너무 달달하다.. 도서관에서 누가 나도 저렇게 봐줬으면 🥺',
          avatarUrl:
              'https://lh3.googleusercontent.com/aida-public/AB6AXuDcmzn0X5PiWxUcn4LMTaPYXELjA6mVdFbg1MPuBTuANif1_MJxX2y8G-_siDxRHrAQ7lID5JSZGzxG0H2pHgbdpq1witBeG1ga341-jNa5nMgaG5Up5oFZ5vpAwDnin8j7izzSrdxSe3dCwa4_NNJsEa3bLibCYGhsXP2-3dTTvMiNhBlau-oSspGd_cKak-goMQPCaVyCDP8qq_NJy9Y4qSxzkmvPgdE7Dq2UvXrGhSiIslmo9j9f5DCk1upuW7S7_nSB7OfcYm3N',
          likeCount: 2,
        ),
        SizedBox(height: 16),
        _CommentItem(
          author: '초록 거북이',
          time: '1시간 전',
          content: '응원합니다! ❤️',
          avatarUrl:
              'https://lh3.googleusercontent.com/aida-public/AB6AXuBO_twnNgicNaiKpHuHeqLjo-Dvuaqzc2zYnpnuRVfTM6RcHd5AaGONjaWlMKf6E3IWhB5QrjWVkG-cn3JoBpujowdDCW4sAwtzcGPEm4l93yzAHy68cufvYSPSNZzvdg5bSNoZwmr1J0VMRvMKvx26SP2qrQ3q-5dcBcY0TxRKAtoMyWgwZj1bLPkiwswv0FIUBNrXM5L41eUk8inxzBuErJtgCTZp44S-YlWoxbBsfZh8ge3YZNtEnNscieyXxGrhXOlVaoGZvhpy',
          likeCount: 1,
        ),
      ],
    );
  }
}

class _CommentItem extends StatelessWidget {
  final String author;
  final String time;
  final String content;
  final String avatarUrl;
  final int likeCount;

  const _CommentItem({
    required this.author,
    required this.time,
    required this.content,
    required this.avatarUrl,
    required this.likeCount,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(radius: 16, backgroundImage: NetworkImage(avatarUrl)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      author,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: _AppColors.textMain,
                      ),
                    ),
                    Text(
                      time,
                      style: TextStyle(fontSize: 12, color: _AppColors.textSub),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  content,
                  style: const TextStyle(
                    fontSize: 14,
                    height: 1.4,
                    color: _AppColors.textBody,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.favorite_rounded,
                      size: 14,
                      color: _AppColors.textSub,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      likeCount > 0 ? '$likeCount' : '좋아요',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: _AppColors.textSub,
                      ),
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
// 하단 입력 바
// =============================================================================
class _BottomInputBar extends StatelessWidget {
  final TextEditingController controller;

  const _BottomInputBar({required this.controller});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.7),
            border: Border(top: BorderSide(color: Colors.grey.shade200)),
          ),
          child: Row(
            children: [
              IconButton(
                onPressed: () {},
                icon: Icon(
                  Icons.add_circle_outline_rounded,
                  color: _AppColors.textSub,
                ),
              ),
              Expanded(
                child: Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: controller,
                          decoration: InputDecoration(
                            hintText: '따뜻한 댓글을 남겨주세요...',
                            hintStyle: TextStyle(
                              color: _AppColors.textSub,
                              fontSize: 14,
                            ),
                            border: InputBorder.none,
                            isDense: true,
                          ),
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: _AppColors.primary,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: _AppColors.primary.withValues(alpha: 0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.arrow_upward_rounded,
                          color: Colors.white,
                          size: 18,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
