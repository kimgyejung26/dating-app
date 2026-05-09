import 'package:flutter/material.dart';
import '../../constants/app_colors.dart';
import '../../widgets/common/profile_card.dart';
import '../../widgets/common/app_button.dart';
import 'profile_detail_screen.dart';

class MatchingScreen extends StatefulWidget {
  const MatchingScreen({super.key});

  @override
  State<MatchingScreen> createState() => _MatchingScreenState();
}

class _MatchingScreenState extends State<MatchingScreen> {
  int _currentCardIndex = 0;
  final PageController _pageController = PageController();

  // 임시 데이터
  final List<Map<String, dynamic>> _matches = [
    {
      'name': 'Ji-min',
      'age': 22,
      'university': 'Seoul National Univ.',
      'major': 'Visual Design',
      'matchPercentage': 98,
      'interests': ['TRAVEL', 'COFFEE'],
      'imageUrl': null,
    },
    {
      'name': 'Min-jun',
      'age': 24,
      'university': 'Seoul National Univ.',
      'major': 'Business Admin',
      'matchPercentage': 94,
      'interests': ['PHOTOGRAPHY', 'MUSIC'],
      'imageUrl': null,
    },
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        backgroundColor: AppColors.backgroundWhite,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.favorite, color: AppColors.primaryPink),
          onPressed: () {},
        ),
        title: const Text(
          '설레연',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.bold,
            fontSize: 20,
          ),
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.primaryPink,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.auto_awesome,
                  color: AppColors.textWhite,
                  size: 16,
                ),
                const SizedBox(width: 4),
                const Text(
                  'AI에게 내 취향 알려주기',
                  style: TextStyle(
                    color: AppColors.textWhite,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                color: AppColors.textPrimary,
                onPressed: () {},
              ),
              Positioned(
                right: 8,
                top: 8,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AppColors.accentRed,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // AI CURATED 태그 및 날짜
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.secondaryPurple,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.auto_awesome,
                          color: AppColors.textWhite,
                          size: 14,
                        ),
                        SizedBox(width: 4),
                        Text(
                          'AI CURATED',
                          style: TextStyle(
                            color: AppColors.textWhite,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Nov 14',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            // 오늘의 설레연 제목
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: const Text(
                '오늘의 설레연',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const SizedBox(height: 16),
            // 프로필 카드 캐러셀
            SizedBox(
              height: 600,
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() {
                    _currentCardIndex = index;
                  });
                },
                itemCount: _matches.length,
                itemBuilder: (context, index) {
                  final match = _matches[index];
                  return ProfileCard(
                    name: match['name'],
                    age: match['age'],
                    university: match['university'],
                    major: match['major'],
                    matchPercentage: match['matchPercentage'],
                    interests: List<String>.from(match['interests']),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => ProfileDetailScreen(
                            profile: match,
                          ),
                        ),
                      );
                    },
                    onLike: () {
                      // 좋아요 처리
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('${match['name']}에게 호감을 보냈습니다'),
                          backgroundColor: AppColors.primaryPink,
                        ),
                      );
                    },
                    onPass: () {
                      // 패스 처리
                      if (_currentCardIndex < _matches.length - 1) {
                        _pageController.nextPage(
                          duration: const Duration(milliseconds: 300),
                          curve: Curves.easeInOut,
                        );
                      }
                    },
                  );
                },
              ),
            ),
            // 페이지 인디케이터
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _matches.length,
                (index) => Container(
                  width: _currentCardIndex == index ? 24 : 8,
                  height: 8,
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    color: _currentCardIndex == index
                        ? AppColors.primaryPink
                        : AppColors.borderLight,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            // 액션 버튼
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Expanded(
                    child: AppButton(
                      text: '프로필 상세',
                      isPrimary: false,
                      isOutlined: true,
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ProfileDetailScreen(
                              profile: _matches[_currentCardIndex],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: AppButton(
                      text: '호감 보내기',
                      icon: Icons.favorite,
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              '${_matches[_currentCardIndex]['name']}에게 호감을 보냈습니다',
                            ),
                            backgroundColor: AppColors.primaryPink,
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // 남은 매칭 횟수
            Center(
              child: Text(
                'You have ${_matches.length - _currentCardIndex - 1} curated matches remaining today',
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 14,
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
