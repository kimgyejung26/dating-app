import 'package:flutter/material.dart';
import '../seol_colors.dart';

/// 설레연 공용 카드 컴포넌트
class SeolCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final Color? backgroundColor;
  final Gradient? gradient;
  final VoidCallback? onTap;
  final bool hasShadow;
  final Border? border;

  const SeolCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = 16,
    this.backgroundColor,
    this.gradient,
    this.onTap,
    this.hasShadow = true,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: gradient == null
            ? (backgroundColor ?? SeolColors.backgroundCard)
            : null,
        gradient: gradient,
        borderRadius: BorderRadius.circular(borderRadius),
        border: border,
        boxShadow: hasShadow
            ? [
                BoxShadow(
                  color: SeolColors.shadowLight,
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(borderRadius),
          child: Padding(
            padding: padding ?? const EdgeInsets.all(16),
            child: child,
          ),
        ),
      ),
    );
  }
}

/// 프로필 카드 (매칭 화면용)
class SeolProfileCard extends StatelessWidget {
  final String name;
  final String? subtitle;
  final String? imageUrl;
  final List<String> tags;
  final VoidCallback? onTap;
  final bool isMystery;

  const SeolProfileCard({
    super.key,
    required this.name,
    this.subtitle,
    this.imageUrl,
    this.tags = const [],
    this.onTap,
    this.isMystery = false,
  });

  @override
  Widget build(BuildContext context) {
    return SeolCard(
      onTap: onTap,
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Image Area
          AspectRatio(
            aspectRatio: 0.75,
            child: Container(
              decoration: BoxDecoration(
                gradient: isMystery
                    ? SeolColors.mysteryGradient
                    : SeolColors.cardGradient,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(16),
                ),
              ),
              child: isMystery
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.person_outline,
                            size: 64,
                            color: SeolColors.textTertiary,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Mystery',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: SeolColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    )
                  : imageUrl != null
                  ? ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(16),
                      ),
                      child: Image.network(
                        imageUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => _buildPlaceholder(),
                      ),
                    )
                  : _buildPlaceholder(),
            ),
          ),
          // Info Area
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isMystery ? '???' : name,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: SeolColors.textPrimary,
                  ),
                ),
                if (subtitle != null && !isMystery) ...[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    style: const TextStyle(
                      fontSize: 14,
                      color: SeolColors.textSecondary,
                    ),
                  ),
                ],
                if (tags.isNotEmpty && !isMystery) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: tags
                        .take(3)
                        .map((tag) => _TagChip(label: tag))
                        .toList(),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      decoration: BoxDecoration(
        gradient: SeolColors.cardGradient,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: Center(
        child: Icon(
          Icons.person,
          size: 80,
          color: SeolColors.primary.withValues(alpha: 0.5),
        ),
      ),
    );
  }
}

class _TagChip extends StatelessWidget {
  final String label;

  const _TagChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: SeolColors.primarySoft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: SeolColors.primary,
        ),
      ),
    );
  }
}

/// 커뮤니티 포스트 카드 (대나무숲용)
class SeolPostCard extends StatelessWidget {
  final String tag;
  final String timeAgo;
  final String content;
  final int likeCount;
  final int commentCount;
  final VoidCallback? onTap;
  final VoidCallback? onLike;

  const SeolPostCard({
    super.key,
    required this.tag,
    required this.timeAgo,
    required this.content,
    this.likeCount = 0,
    this.commentCount = 0,
    this.onTap,
    this.onLike,
  });

  Color get _tagColor {
    switch (tag) {
      case '썸사랑':
      case '두근':
        return SeolColors.tagExcitement;
      case '첫만남':
      case '첫미팅':
        return SeolColors.tagFirstMeet;
      case '고민':
        return SeolColors.tagWorry;
      case '성공후기':
      case '오늘의 추천':
        return SeolColors.tagSuccess;
      default:
        return SeolColors.primarySoft;
    }
  }

  @override
  Widget build(BuildContext context) {
    return SeolCard(
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Tag & Time
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _tagColor,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  tag,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: SeolColors.primary,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                timeAgo,
                style: TextStyle(fontSize: 12, color: SeolColors.textTertiary),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Content
          Text(
            content,
            style: TextStyle(
              fontSize: 14,
              color: SeolColors.textPrimary,
              height: 1.5,
            ),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),
          // Actions
          Row(
            children: [
              InkWell(
                onTap: onLike,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.all(4),
                  child: Row(
                    children: [
                      Icon(
                        Icons.favorite_border,
                        size: 18,
                        color: SeolColors.textTertiary,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '$likeCount',
                        style: TextStyle(
                          fontSize: 13,
                          color: SeolColors.textTertiary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Row(
                children: [
                  Icon(
                    Icons.chat_bubble_outline,
                    size: 18,
                    color: SeolColors.textTertiary,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '$commentCount',
                    style: TextStyle(
                      fontSize: 13,
                      color: SeolColors.textTertiary,
                    ),
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
