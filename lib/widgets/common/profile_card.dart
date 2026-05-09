import 'package:flutter/material.dart';
import '../../constants/app_colors.dart';

class ProfileCard extends StatelessWidget {
  final String name;
  final int age;
  final String? university;
  final String? major;
  final int matchPercentage;
  final String? imageUrl;
  final List<String> interests;
  final VoidCallback? onTap;
  final VoidCallback? onLike;
  final VoidCallback? onPass;

  const ProfileCard({
    super.key,
    required this.name,
    required this.age,
    this.university,
    this.major,
    required this.matchPercentage,
    this.imageUrl,
    this.interests = const [],
    this.onTap,
    this.onLike,
    this.onPass,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.backgroundWhite,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 이미지 영역
            Stack(
              children: [
                ClipRRect(
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(20),
                  ),
                  child: imageUrl != null
                      ? Image.network(
                          imageUrl!,
                          width: double.infinity,
                          height: 400,
                          fit: BoxFit.cover,
                        )
                      : Container(
                          width: double.infinity,
                          height: 400,
                          color: AppColors.backgroundGrey,
                          child: const Icon(
                            Icons.person,
                            size: 100,
                            color: AppColors.textTertiary,
                          ),
                        ),
                ),
                // 매칭 퍼센트 배지
                Positioned(
                  top: 16,
                  left: 16,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.accentGreen.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.star,
                          color: AppColors.textWhite,
                          size: 16,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '$matchPercentage% Match',
                          style: const TextStyle(
                            color: AppColors.textWhite,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            // 정보 영역
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 이름과 나이
                  Text(
                    '$name, $age',
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  // 대학 및 전공
                  if (university != null || major != null)
                    Row(
                      children: [
                        const Icon(
                          Icons.school,
                          size: 16,
                          color: AppColors.textSecondary,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          [university, major].where((e) => e != null).join(' • '),
                          style: const TextStyle(
                            fontSize: 14,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  const SizedBox(height: 12),
                  // 관심사 태그
                  if (interests.isNotEmpty)
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: interests.map((interest) {
                        return Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.backgroundGrey,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Text(
                            interest,
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                ],
              ),
            ),
            // 액션 버튼
            if (onLike != null || onPass != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    if (onPass != null)
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: onPass,
                          icon: const Icon(Icons.close),
                          label: const Text('Pass'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppColors.textSecondary,
                            side: const BorderSide(
                              color: AppColors.borderLight,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    if (onLike != null && onPass != null)
                      const SizedBox(width: 12),
                    if (onLike != null)
                      Expanded(
                        flex: onPass != null ? 1 : 0,
                        child: ElevatedButton.icon(
                          onPressed: onLike,
                          icon: const Icon(Icons.favorite),
                          label: const Text('Like'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primaryPink,
                            foregroundColor: AppColors.textWhite,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
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
