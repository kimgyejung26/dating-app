import 'package:flutter/material.dart';
import '../../constants/app_colors.dart';
import '../../widgets/common/app_button.dart';

class EventRouletteScreen extends StatelessWidget {
  const EventRouletteScreen({super.key});

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
          '3:3 시즌 미팅',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.secondaryPurpleLight,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.star,
                  color: AppColors.secondaryPurple,
                  size: 16,
                ),
                const SizedBox(width: 4),
                const Text(
                  '5',
                  style: TextStyle(
                    color: AppColors.secondaryPurple,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFE1BEE7),
              Color(0xFFF3E5F5),
              Color(0xFFFFE0B2),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 32),
              // 제목
              const Text(
                '3:3 시즌 미팅',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '한 번뿐인 랜덤 매칭',
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 48),
              // 슬롯 머신 영역
              Expanded(
                child: Center(
                  child: Container(
                    width: 350,
                    height: 500,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppColors.backgroundWhite,
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.2),
                          blurRadius: 20,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        // 2x3 그리드 프로필 슬롯
                        Expanded(
                          child: GridView.builder(
                            gridDelegate:
                                const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              crossAxisSpacing: 12,
                              mainAxisSpacing: 12,
                              childAspectRatio: 0.7,
                            ),
                            itemCount: 6,
                            itemBuilder: (context, index) {
                              final isBlurred = index < 3;
                              return Container(
                                decoration: BoxDecoration(
                                  color: AppColors.backgroundGrey,
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: AppColors.borderLight,
                                    width: 2,
                                  ),
                                ),
                                child: isBlurred
                                    ? Stack(
                                        children: [
                                          Container(
                                            decoration: BoxDecoration(
                                              color: AppColors.backgroundGrey,
                                              borderRadius:
                                                  BorderRadius.circular(14),
                                            ),
                                          ),
                                          Center(
                                            child: Icon(
                                              Icons.person,
                                              size: 40,
                                              color: AppColors.textTertiary,
                                            ),
                                          ),
                                        ],
                                      )
                                    : Container(
                                        decoration: BoxDecoration(
                                          color: AppColors.backgroundGrey,
                                          borderRadius: BorderRadius.circular(14),
                                        ),
                                        child: const Icon(
                                          Icons.person,
                                          size: 40,
                                          color: AppColors.textTertiary,
                                        ),
                                      ),
                              );
                            },
                          ),
                        ),
                        // 레버
                        Container(
                          margin: const EdgeInsets.only(top: 20),
                          width: 60,
                          height: 100,
                          decoration: BoxDecoration(
                            color: AppColors.accentRed,
                            borderRadius: BorderRadius.circular(30),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.3),
                                blurRadius: 10,
                                offset: const Offset(0, 5),
                              ),
                            ],
                          ),
                          child: const Center(
                            child: Icon(
                              Icons.arrow_downward,
                              color: AppColors.textWhite,
                              size: 30,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 32),
              // 이상형 룰렛 돌리기 버튼
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: AppButton(
                  text: '이상형 룰렛 돌리기',
                  onPressed: () {
                    // 룰렛 돌리기 로직
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('룰렛을 돌리는 중...'),
                        backgroundColor: AppColors.secondaryPurple,
                      ),
                    );
                  },
                  backgroundColor: AppColors.secondaryPurple,
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
