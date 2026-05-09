/// 설레연 앱 Mock 데이터 - 대나무숲 게시글
class MockPost {
  final String id;
  final String tag;
  final String content;
  final String timeAgo;
  final int likeCount;
  final int commentCount;
  final bool isHighlighted;

  const MockPost({
    required this.id,
    required this.tag,
    required this.content,
    required this.timeAgo,
    this.likeCount = 0,
    this.commentCount = 0,
    this.isHighlighted = false,
  });
}

/// 목 대나무숲 게시글 데이터
class MockPosts {
  MockPosts._();

  static const List<MockPost> posts = [
    MockPost(
      id: 'p1',
      tag: '썸사랑',
      content:
          'Is it weird that I still think about the coffee we had yesterday? I barely slept because my heart was racing so fast.',
      timeAgo: '10 mins ago',
      likeCount: 24,
      commentCount: 5,
    ),
    MockPost(
      id: 'p2',
      tag: '첫만남',
      content:
          'Meeting someone from the app for the first time in Gangnam tonight. Wish me luck! Does this outfit look okay? 🌸',
      timeAgo: '35 mins ago',
      likeCount: 156,
      commentCount: 32,
    ),
    MockPost(
      id: 'p3',
      tag: '고민',
      content:
          'I want to text him first, but I\'m afraid of seeming too desperate. Why is dating so hard? 😕',
      timeAgo: '1 hour ago',
      likeCount: 12,
      commentCount: 15,
    ),
    MockPost(
      id: 'p4',
      tag: '오늘의 추천',
      content: 'Perfect date spots for cherry blossom season 🌸',
      timeAgo: '2 hours ago',
      likeCount: 89,
      commentCount: 12,
      isHighlighted: true,
    ),
    MockPost(
      id: 'p5',
      tag: '성공후기',
      content: '설레연에서 만나서 3개월째 연애 중이에요! 처음 대화 시작할 때 정말 떨렸는데 지금은 너무 행복해요 💕',
      timeAgo: '3 hours ago',
      likeCount: 234,
      commentCount: 45,
    ),
    MockPost(
      id: 'p6',
      tag: '두근',
      content: '오늘 매칭된 분이랑 첫 대화했는데... 취향이 너무 비슷해서 소름돋았어요 😳',
      timeAgo: '4 hours ago',
      likeCount: 67,
      commentCount: 8,
    ),
  ];

  static const List<String> filterTabs = [
    '전체 (All)',
    '인기 (Popular)',
    '설렘 (Excitement)',
  ];

  static const List<String> emotionTags = [
    '두근',
    '첫미팅',
    '고민',
    '썸사랑',
    '성공후기',
    '오늘의 추천',
  ];
}
