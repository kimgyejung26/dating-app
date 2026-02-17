// =============================================================================
// 관심사 선택 화면
// 경로: lib/features/onboarding/screens/interests_selection_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const InterestsSelectionScreen()),
// );
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../router/route_names.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFFFF4B6E);
  static const Color backgroundLight = Color(0xFFFFFFFF);
  static const Color surfaceLight = Color(0xFFF8F9FA);
  static const Color textMain = Color(0xFF1A1A1A);
  static const Color textSub = Color(0xFF6B7280);
  static const Color chipBg = Color(0xFFF3F4F6);
  static const Color chipSelected = Color(0xFF4B5563);
  static const Color border = Color(0xFFE5E7EB);
  static const Color progressBg = Color(0xFFE6DBDF);
}

// =============================================================================
// 데이터 모델
// =============================================================================
class InterestCategory {
  final String emoji;
  final String title;
  final List<String> items;

  const InterestCategory({
    required this.emoji,
    required this.title,
    required this.items,
  });
}

const List<InterestCategory> _categories = [
  InterestCategory(
    emoji: '🏠',
    title: 'Inside Activity',
    items: [
      '넷플릭스',
      '홈트',
      '드라마 정주행',
      '온라인 쇼핑',
      '식물 가꾸기',
      '보드게임',
      '명상',
      '요가',
      '사우나',
      '유튜브',
      '먹방',
      '도서관',
      '노래',
      '시',
      '문학',
      '댄스',
      '독서',
      '카공',
      '공부',
    ],
  ),
  InterestCategory(
    emoji: '⛺',
    title: 'Outside Activity',
    items: [
      '한강에서 치맥',
      '빈티지 쇼핑',
      '동네 산책',
      '만화 카페',
      '방탈출',
      '카페 탐방',
      '맛집 투어',
      '브런치',
      '수제 맥주',
      '바',
      '자동차 극장',
      '콘서트',
      '아쿠아리움',
      '쇼핑',
      '전시회',
      '연극',
      '롤러 스케이트',
      '노래방',
      '야경 보기',
      '캠핑',
      '서핑',
      '낚시',
      '피크닉',
      '다이빙',
      '여행',
      '오락실',
      '노상',
      '새벽 라면',
      '바다 보기',
      '사진',
      '스케이트',
    ],
  ),
  InterestCategory(
    emoji: '🍷',
    title: 'Eat & Drink',
    items: [
      '칵테일',
      '맥주',
      '빵',
      '양식',
      '스시',
      '일식',
      '해산물',
      '한식',
      '중식',
      '버블티',
      '차',
      '커피',
      '와인',
      'BBQ',
      '라면',
      '디저트',
      '아이스크림',
      '훠궈',
      '양꼬치',
      '붕어빵',
      '과일',
    ],
  ),
  InterestCategory(
    emoji: '⚽️',
    title: '운동, 스포츠',
    items: [
      '야구',
      '축구',
      '스포츠',
      '배드민턴',
      '헬스장',
      '수영',
      '클라이밍',
      '피트니스',
      '필라테스',
      '농구',
      '러닝',
      '스케이트보드',
      '럭비',
      '크로스핏',
      '산책',
      '폴 댄스',
      '테니스',
      '복싱',
      '역도',
      '마라톤',
      '승마',
      '배구',
      '탁구',
      '당구',
      '사이클',
      '볼링',
      '사격',
      '스키',
      '스노우 보드',
    ],
  ),
  InterestCategory(
    emoji: '🎬',
    title: '드라마, 영화',
    items: [
      'K-드라마',
      '애니메이션',
      '액션 영화',
      '드라마',
      '판타지 영화',
      'SF',
      '영화',
      '공포 영화',
      '로맨틱 코미디',
      '범죄 영화',
      '리얼리티 프로그램',
      '스릴러',
      '코미디',
    ],
  ),
  InterestCategory(
    emoji: '🎵',
    title: '음악',
    items: [
      '팝',
      '발라드',
      '락/밴드',
      '인디/얼터너티브',
      '힙합',
      'J-Pop',
      '일렉트로닉 음악',
      '클래식',
      '재즈/R&B',
      '헤비메탈',
      '마이너 음악',
    ],
  ),
  InterestCategory(
    emoji: '🎮',
    title: '게임',
    items: ['PC방', '롤', '오버워치', '플스', '닌텐도', '인디게임'],
  ),
  InterestCategory(
    emoji: '🎨',
    title: 'Creativity',
    items: [
      '언어 교환',
      '악기',
      '창업',
      '패션',
      '블로그',
      '콘텐츠 제작',
      '메이크업',
      '요리',
      '글쓰기',
      '예술',
      '작곡',
      '베이킹',
      '드로잉',
    ],
  ),
  InterestCategory(
    emoji: '👥',
    title: '소셜',
    items: ['수다', '친구 만나기', '인스타그램', '브이로그', '소셜 미디어', '핀터레스트', '블로그'],
  ),
];

// =============================================================================
// 메인 화면
// =============================================================================
class InterestsSelectionScreen extends StatefulWidget {
  final VoidCallback? onClose;
  final VoidCallback? onComplete;
  final VoidCallback? onBack;
  final int maxSelection;
  final int currentStep;
  final int totalSteps;

  const InterestsSelectionScreen({
    super.key,
    this.onClose,
    this.onComplete,
    this.onBack,
    this.maxSelection = 10,
    this.currentStep = 2,
    this.totalSteps = 8,
  });

  @override
  State<InterestsSelectionScreen> createState() =>
      _InterestsSelectionScreenState();
}

class _InterestsSelectionScreenState extends State<InterestsSelectionScreen> {
  final Set<String> _selectedInterests = {
    '악기',
    '빈티지 쇼핑',
    '한강에서 치맥',
    '넷플릭스',
  }; // 초기 데이터 예시

  void _toggleInterest(String interest) {
    HapticFeedback.lightImpact();
    setState(() {
      if (_selectedInterests.contains(interest)) {
        _selectedInterests.remove(interest);
      } else {
        if (_selectedInterests.length < widget.maxSelection) {
          _selectedInterests.add(interest);
        } else {
          // 최대 선택 개수 초과 시 피드백
          HapticFeedback.mediumImpact();
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.backgroundLight,
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                // 헤더
                _Header(
                  currentStep: widget.currentStep,
                  totalSteps: widget.totalSteps,
                  onBack: widget.onBack,
                ),
                // 메인 콘텐츠
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(20, 0, 20, 100),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 16),
                        // 타이틀 및 카운터
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            const Text(
                              '관심사',
                              style: TextStyle(
                                fontFamily: 'Noto Sans KR',
                                fontSize: 28,
                                fontWeight: FontWeight.bold,
                                color: _AppColors.textMain,
                                letterSpacing: -0.5,
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text(
                                '${_selectedInterests.length}/${widget.maxSelection}',
                                style: const TextStyle(
                                  fontFamily: 'Noto Sans KR',
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: _AppColors.textSub,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        // 선택된 관심사 칩 영역
                        if (_selectedInterests.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 24),
                            child: Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: _selectedInterests.map((interest) {
                                return _SelectedChip(
                                  label: interest,
                                  onDeleted: () => _toggleInterest(interest),
                                );
                              }).toList(),
                            ),
                          ),
                        // 검색창
                        const _SearchBar(),
                        const SizedBox(height: 32),
                        // 카테고리별 섹션
                        ..._categories.map(
                          (category) => _CategorySection(
                            category: category,
                            selectedInterests: _selectedInterests,
                            onToggle: _toggleInterest,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            // 하단 플로팅 버튼 (다음 클릭 → lifestyle_screen)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _BottomFloatingArea(
                onNext:
                    widget.onComplete ??
                    () {
                      Navigator.of(
                        context,
                      ).pushNamed(RouteNames.onboardingLifestyle);
                    },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final int currentStep;
  final int totalSteps;
  final VoidCallback? onBack;

  const _Header({
    required this.currentStep,
    required this.totalSteps,
    this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: _AppColors.backgroundLight.withValues(alpha: 0.8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            onPressed: () {
              HapticFeedback.lightImpact();
              if (onBack != null) {
                onBack!.call();
              } else {
                Navigator.of(context).pop();
              }
            },
            icon: const Icon(
              Icons.arrow_back_rounded,
              color: _AppColors.textMain,
              size: 24,
            ),
            style: IconButton.styleFrom(
              padding: const EdgeInsets.all(8),
              backgroundColor: Colors.transparent,
            ),
          ),
          // 커스텀 프로그레스 인디케이터
          Row(
            children: List.generate(totalSteps, (index) {
              final isCurrent = index == currentStep - 1;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: isCurrent ? 24 : 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: isCurrent ? _AppColors.primary : _AppColors.progressBg,
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
          const SizedBox(width: 40),
        ],
      ),
    );
  }
}

// =============================================================================
// 선택된 관심사 칩
// =============================================================================
class _SelectedChip extends StatelessWidget {
  final String label;
  final VoidCallback onDeleted;

  const _SelectedChip({required this.label, required this.onDeleted});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _AppColors.chipSelected,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: Colors.white,
            ),
          ),
          const SizedBox(width: 4),
          GestureDetector(
            onTap: onDeleted,
            child: const Icon(
              Icons.close_rounded,
              color: Colors.white70,
              size: 16,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 검색창
// =============================================================================
class _SearchBar extends StatelessWidget {
  const _SearchBar();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: TextField(
        decoration: InputDecoration(
          filled: true,
          fillColor: _AppColors.surfaceLight,
          hintText: '검색',
          hintStyle: const TextStyle(color: _AppColors.textSub),
          prefixIcon: const Icon(
            Icons.search_rounded,
            color: _AppColors.textSub,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide.none,
          ),
          contentPadding: const EdgeInsets.symmetric(vertical: 16),
        ),
      ),
    );
  }
}

// =============================================================================
// 카테고리 섹션
// =============================================================================
class _CategorySection extends StatefulWidget {
  final InterestCategory category;
  final Set<String> selectedInterests;
  final Function(String) onToggle;

  const _CategorySection({
    required this.category,
    required this.selectedInterests,
    required this.onToggle,
  });

  @override
  State<_CategorySection> createState() => _CategorySectionState();
}

class _CategorySectionState extends State<_CategorySection> {
  bool _isExpanded = false;

  // 2줄에 해당하는 높이 (칩 높이 약 40 + runSpacing 10) * 2
  static const double _collapsedHeight = 90.0;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 섹션 헤더
          Row(
            children: [
              Text(widget.category.emoji, style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 8),
              Text(
                widget.category.title,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: _AppColors.textMain,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 칩 목록 (확장 상태에 따라 높이 제한)
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 300),
            crossFadeState: _isExpanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            firstChild: SizedBox(
              height: _collapsedHeight,
              child: ClipRect(
                child: Wrap(
                  spacing: 8,
                  runSpacing: 10,
                  children: widget.category.items.map((item) {
                    final isSelected = widget.selectedInterests.contains(item);
                    return _InterestOptionChip(
                      label: item,
                      isSelected: isSelected,
                      onTap: () => widget.onToggle(item),
                    );
                  }).toList(),
                ),
              ),
            ),
            secondChild: Wrap(
              spacing: 8,
              runSpacing: 10,
              children: widget.category.items.map((item) {
                final isSelected = widget.selectedInterests.contains(item);
                return _InterestOptionChip(
                  label: item,
                  isSelected: isSelected,
                  onTap: () => widget.onToggle(item),
                );
              }).toList(),
            ),
          ),
          // 더 보기 / 접기 버튼
          const SizedBox(height: 24),
          GestureDetector(
            onTap: () {
              HapticFeedback.lightImpact();
              setState(() {
                _isExpanded = !_isExpanded;
              });
            },
            child: Row(
              children: [
                Expanded(child: Container(height: 1, color: _AppColors.border)),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Row(
                    children: [
                      Text(
                        _isExpanded ? '접기' : '더 보기',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: _AppColors.textMain,
                        ),
                      ),
                      AnimatedRotation(
                        turns: _isExpanded ? 0.5 : 0,
                        duration: const Duration(milliseconds: 300),
                        child: const Icon(
                          Icons.expand_more_rounded,
                          size: 16,
                          color: _AppColors.textMain,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(child: Container(height: 1, color: _AppColors.border)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InterestOptionChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _InterestOptionChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : _AppColors.chipBg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? _AppColors.primary : Colors.transparent,
            width: isSelected ? 2 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: _AppColors.primary.withValues(alpha: 0.2),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ]
              : [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.02),
                    blurRadius: 2,
                    offset: const Offset(0, 1),
                  ),
                ],
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? _AppColors.primary : _AppColors.textSub,
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// 하단 플로팅 영역
// =============================================================================
class _BottomFloatingArea extends StatelessWidget {
  final VoidCallback? onNext;

  const _BottomFloatingArea({this.onNext});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _AppColors.backgroundLight.withValues(alpha: 0),
            _AppColors.backgroundLight.withValues(alpha: 0.95),
            _AppColors.backgroundLight,
          ],
        ),
      ),
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        MediaQuery.of(context).padding.bottom + 20,
      ),
      child: CupertinoButton(
        padding: EdgeInsets.zero,
        onPressed: () {
          HapticFeedback.mediumImpact();
          onNext?.call();
        },
        child: Container(
          height: 56,
          width: double.infinity,
          decoration: BoxDecoration(
            color: _AppColors.primary,
            borderRadius: BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(
                color: _AppColors.primary.withValues(alpha: 0.3),
                blurRadius: 12,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Text(
                '다음으로',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              SizedBox(width: 8),
              Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
