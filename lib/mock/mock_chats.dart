/// 설레연 앱 Mock 데이터 - 채팅
class MockChatRoom {
  final String id;
  final String name;
  final String? imageUrl;
  final String lastMessage;
  final String timeAgo;
  final int unreadCount;
  final bool isGroupChat;
  final bool isAi;

  const MockChatRoom({
    required this.id,
    required this.name,
    this.imageUrl,
    required this.lastMessage,
    required this.timeAgo,
    this.unreadCount = 0,
    this.isGroupChat = false,
    this.isAi = false,
  });
}

class MockMessage {
  final String id;
  final String content;
  final bool isMe;
  final String time;

  const MockMessage({
    required this.id,
    required this.content,
    required this.isMe,
    required this.time,
  });
}

/// 목 채팅 데이터
class MockChats {
  MockChats._();

  static const List<MockChatRoom> oneToOneChats = [
    MockChatRoom(
      id: 'c1',
      name: '김지수',
      lastMessage: '오늘 저녁에 시간 어때요? 강남역 근처에...',
      timeAgo: '방금 전',
      unreadCount: 2,
    ),
    MockChatRoom(
      id: 'c2',
      name: '박민준',
      lastMessage: '반가워요! 프로필 사진 분위기가 정말 좋...',
      timeAgo: '10분 전',
      unreadCount: 1,
    ),
    MockChatRoom(
      id: 'c3',
      name: '이서연',
      lastMessage: '네 알겠습니다~ 그럼 주말에 뵙는 걸로 할게...',
      timeAgo: '1시간 전',
    ),
    MockChatRoom(
      id: 'c4',
      name: '최현우',
      lastMessage: '사진 보내드렸습니다. 확인해주세요...',
      timeAgo: '어제',
    ),
    MockChatRoom(
      id: 'c5',
      name: '정하나',
      lastMessage: '즐거운 하루 보내세요 :)',
      timeAgo: '어제',
    ),
  ];

  static const List<MockChatRoom> groupChats = [
    MockChatRoom(
      id: 'g1',
      name: '연대 × 고대 3:3',
      lastMessage: '다들 금요일 괜찮으신가요?',
      timeAgo: '30분 전',
      isGroupChat: true,
      unreadCount: 5,
    ),
    MockChatRoom(
      id: 'g2',
      name: '서울대 × 이대 3:3',
      lastMessage: '장소 정하면 알려드릴게요!',
      timeAgo: '2시간 전',
      isGroupChat: true,
    ),
  ];

  static const List<MockChatRoom> aiChats = [
    MockChatRoom(
      id: 'ai1',
      name: 'AI 어시스턴트',
      lastMessage: '프로필 작성에 도움이 필요하시면 말씀해주세요!',
      timeAgo: '1일 전',
      isAi: true,
    ),
  ];

  static const List<MockMessage> sampleConversation = [
    MockMessage(
      id: '1',
      content: '안녕하세요! 반가워요 😊',
      isMe: false,
      time: '오후 2:30',
    ),
    MockMessage(
      id: '2',
      content: '안녕하세요~ 프로필 보고 연락드려요!',
      isMe: true,
      time: '오후 2:31',
    ),
    MockMessage(
      id: '3',
      content: '오 감사해요! 혹시 어느 학교 다니세요?',
      isMe: false,
      time: '오후 2:32',
    ),
    MockMessage(
      id: '4',
      content: '성균관대 다녀요! 취미가 여행이라고 하셨는데',
      isMe: true,
      time: '오후 2:33',
    ),
    MockMessage(
      id: '5',
      content: '저도 여행 좋아해서요 ㅎㅎ',
      isMe: true,
      time: '오후 2:33',
    ),
    MockMessage(
      id: '6',
      content: '오 그럼 혹시 요즘 가고 싶은 곳 있어요?',
      isMe: false,
      time: '오후 2:35',
    ),
  ];
}
