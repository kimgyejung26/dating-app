import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../design_system/design_system.dart';
import '../../services/storage_service.dart';

class TutorialScreen extends StatefulWidget {
  const TutorialScreen({super.key});

  @override
  State<TutorialScreen> createState() => _TutorialScreenState();
}

class _TutorialScreenState extends State<TutorialScreen> {
  final PageController _pageController = PageController();
  final StorageService _storageService = StorageService();
  int _currentPage = 0;

  final List<_TutorialPage> _pages = [
    _TutorialPage(
      icon: Icons.navigation_outlined,
      title: '앱 하단 바 설명',
      subtitle: '어디로든 빠르게 이동해요',
      description: '하단 탭을 누르면 원하는 메뉴로 바로 이동할 수 있어요',
      features: ['설레연', '채팅', '이벤트', '대나무숲', '내 페이지'],
    ),
    _TutorialPage(
      icon: Icons.favorite_border,
      title: '1:1 매칭',
      subtitle: '오늘의 추천 이성을 만나보세요',
      description: '매일 새로운 추천 프로필을 확인하고\n마음에 드는 분께 하트를 보내보세요',
      features: ['프로필 확인', '하트 보내기', 'AI 맞춤 추천'],
    ),
    _TutorialPage(
      icon: Icons.smart_toy_outlined,
      title: 'AI 어시스턴트',
      subtitle: '연애 고민, AI가 도와드려요',
      description: '프로필 작성부터 대화 팁까지\nAI가 맞춤 조언을 제공해요',
      features: ['프로필 코칭', '대화 조언', '맞춤 추천'],
    ),
    _TutorialPage(
      icon: Icons.group_outlined,
      title: '3:3 랜덤 매칭',
      subtitle: '새로운 인연을 찾아보세요',
      description: '혼자서도 참여 가능! 노페이스 옵션으로\n부담 없이 새로운 만남을 시작해요',
      features: ['1인 참여 가능', '노페이스 기본', '약속 머니 시스템'],
    ),
    _TutorialPage(
      icon: Icons.forest_outlined,
      title: '대나무숲',
      subtitle: '익명 연애 커뮤니티',
      description: '연애 고민, 성공 후기, 첫 만남 설렘을\n익명으로 자유롭게 나눠요',
      features: ['익명 게시', '감정 태그', '공감 & 댓글'],
    ),
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      useGradient: true,
      body: SafeArea(
        child: Column(
          children: [
            // Skip Button
            Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: TextButton(
                  onPressed: _completeTutorial,
                  child: Text(
                    '건너뛰기',
                    style: SeolTypography.labelMedium.copyWith(
                      color: SeolColors.textSecondary,
                    ),
                  ),
                ),
              ),
            ),
            // Page Counter
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: SeolColors.primarySoft,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                'Page ${_currentPage + 1} of ${_pages.length}',
                style: SeolTypography.labelSmall.copyWith(
                  color: SeolColors.primary,
                ),
              ),
            ),
            // Page View
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) => setState(() => _currentPage = index),
                itemCount: _pages.length,
                itemBuilder: (context, index) => _buildPage(_pages[index]),
              ),
            ),
            // Page Indicator
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _pages.length,
                (index) => _buildIndicator(index == _currentPage),
              ),
            ),
            const SizedBox(height: 32),
            // Next/Complete Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: SeolButton(
                text: _currentPage == _pages.length - 1 ? '시작하기' : '다음',
                onPressed: _currentPage == _pages.length - 1
                    ? _completeTutorial
                    : _nextPage,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPage(_TutorialPage page) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Icon
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              gradient: SeolColors.primaryGradient,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: SeolColors.primary.withValues(alpha: 0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Icon(page.icon, size: 48, color: SeolColors.textWhite),
          ),
          const SizedBox(height: 32),
          // Title
          Text(
            page.title,
            style: SeolTypography.h2,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            page.subtitle,
            style: SeolTypography.bodyLarge.copyWith(color: SeolColors.primary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          Text(
            page.description,
            style: SeolTypography.bodyMedium.copyWith(
              color: SeolColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          // Feature Tags
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: page.features.map((feature) {
              return SeolChip(label: feature, type: SeolChipType.emotion);
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildIndicator(bool isActive) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.symmetric(horizontal: 4),
      width: isActive ? 24 : 8,
      height: 8,
      decoration: BoxDecoration(
        color: isActive ? SeolColors.primary : SeolColors.borderMedium,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  void _nextPage() {
    _pageController.nextPage(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  void _completeTutorial() async {
    await _storageService.setTutorialSeen();
    if (mounted) {
      context.go('/main');
    }
  }
}

class _TutorialPage {
  final IconData icon;
  final String title;
  final String subtitle;
  final String description;
  final List<String> features;

  _TutorialPage({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.description,
    required this.features,
  });
}
