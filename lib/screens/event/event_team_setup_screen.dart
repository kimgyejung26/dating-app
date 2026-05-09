import 'package:flutter/material.dart';
import '../../constants/app_colors.dart';
import '../../widgets/common/app_button.dart';
import 'event_roulette_screen.dart';

class EventTeamSetupScreen extends StatelessWidget {
  const EventTeamSetupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        backgroundColor: AppColors.backgroundWhite,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          '3명 팀으로 참여해요',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '팀 구성하기',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '친구 2명을 초대해서 팀을 완성해보세요.',
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 32),
              // 팀 멤버 슬롯
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildTeamSlot(
                    isMe: true,
                    name: '지수',
                    mbti: 'ESTJ',
                    color: AppColors.primaryPinkLight,
                  ),
                  _buildTeamSlot(
                    isMe: false,
                    name: '친구 초대',
                    isEmpty: true,
                  ),
                  _buildTeamSlot(
                    isMe: false,
                    name: '친구 초대',
                    isEmpty: true,
                  ),
                ],
              ),
              const SizedBox(height: 24),
              // 안내 메시지
              Row(
                children: [
                  const Icon(
                    Icons.info_outline,
                    color: AppColors.textSecondary,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    '3명이 모여야 매칭을 시작할 수 있어요',
                    style: TextStyle(
                      fontSize: 14,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 32),
              // 초대 버튼
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        // 카카오 초대
                      },
                      icon: const Icon(Icons.chat),
                      label: const Text('카카오로 초대'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.textPrimary,
                        side: const BorderSide(color: AppColors.borderLight),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        // 링크 복사
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('링크가 복사되었습니다'),
                          ),
                        );
                      },
                      icon: const Icon(Icons.link),
                      label: const Text('링크 복사'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.textPrimary,
                        side: const BorderSide(color: AppColors.borderLight),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              // 슬롯머신 돌리기 버튼
              AppButton(
                text: '슬롯머신 돌리기 (1회 무료)',
                icon: Icons.casino,
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const EventRouletteScreen(),
                    ),
                  );
                },
                backgroundColor: AppColors.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTeamSlot({
    required bool isMe,
    required String name,
    String? mbti,
    Color? color,
    bool isEmpty = false,
  }) {
    return Container(
      width: 100,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isEmpty ? AppColors.backgroundWhite : color ?? AppColors.backgroundWhite,
        borderRadius: BorderRadius.circular(16),
        border: isEmpty
            ? Border.all(
                color: AppColors.primaryPinkLight,
                width: 2,
                style: BorderStyle.solid,
              )
            : null,
      ),
      child: Column(
        children: [
          if (isMe)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primaryPink,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'ME',
                style: TextStyle(
                  color: AppColors.textWhite,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            )
          else if (isEmpty)
            const SizedBox(height: 20),
          const SizedBox(height: 8),
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              color: isEmpty
                  ? Colors.transparent
                  : (color ?? AppColors.backgroundGrey),
              shape: BoxShape.circle,
            ),
            child: isEmpty
                ? const Icon(
                    Icons.add,
                    color: AppColors.primaryPink,
                    size: 30,
                  )
                : const Icon(
                    Icons.person,
                    size: 30,
                    color: AppColors.textTertiary,
                  ),
          ),
          const SizedBox(height: 8),
          Text(
            name,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: isEmpty ? AppColors.primaryPink : AppColors.textPrimary,
            ),
          ),
          if (mbti != null) ...[
            const SizedBox(height: 4),
            Text(
              mbti,
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
