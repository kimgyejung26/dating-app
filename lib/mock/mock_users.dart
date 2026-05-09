/// 설레연 앱 Mock 데이터 - 사용자 프로필
class MockUser {
  final String id;
  final String name;
  final String? nickname;
  final int age;
  final String university;
  final String department;
  final int grade;
  final String? mbti;
  final int? height;
  final String? imageUrl;
  final List<String> tags;
  final String? introduction;
  final bool isMystery;

  const MockUser({
    required this.id,
    required this.name,
    this.nickname,
    required this.age,
    required this.university,
    required this.department,
    required this.grade,
    this.mbti,
    this.height,
    this.imageUrl,
    this.tags = const [],
    this.introduction,
    this.isMystery = false,
  });

  String get subtitle => '$university $department $grade학년';
}

/// 목 사용자 데이터
class MockUsers {
  MockUsers._();

  static const List<MockUser> recommendations = [
    MockUser(
      id: '1',
      name: 'Ji-min',
      nickname: '지민',
      age: 23,
      university: '연세대학교',
      department: '경영학과',
      grade: 3,
      mbti: 'ENFP',
      height: 168,
      tags: ['여행', 'ENFP', '카페투어'],
      introduction: '같이 맛집 탐방해요! 🍽️',
    ),
    MockUser(
      id: '2',
      name: '김지수',
      nickname: '지수',
      age: 24,
      university: '고려대학교',
      department: '컴퓨터공학과',
      grade: 4,
      mbti: 'INTJ',
      height: 175,
      tags: ['운동', '독서', '개발'],
      introduction: '코딩하다 쉴 때 연락주세요',
    ),
    MockUser(
      id: '3',
      name: '박민준',
      nickname: '민준',
      age: 22,
      university: '서울대학교',
      department: '의예과',
      grade: 2,
      mbti: 'ISFP',
      height: 180,
      tags: ['피아노', '영화', '카메라'],
      introduction: '감성 충만한 대화 좋아해요',
    ),
    MockUser(
      id: '4',
      name: '이서연',
      nickname: '서연',
      age: 21,
      university: '이화여자대학교',
      department: '심리학과',
      grade: 2,
      mbti: 'INFJ',
      height: 163,
      tags: ['심리', '책', '그림'],
      introduction: '마음을 읽어드릴게요 💜',
    ),
    MockUser(
      id: '5',
      name: '최현우',
      nickname: '현우',
      age: 25,
      university: '한양대학교',
      department: '기계공학과',
      grade: 4,
      mbti: 'ESTP',
      height: 182,
      tags: ['헬스', '농구', '드라이브'],
      introduction: '활동적인 데이트 좋아합니다',
    ),
  ];

  // 3:3 매칭용 Mystery 사용자
  static const List<MockUser> mysteryUsers = [
    MockUser(
      id: 'm1',
      name: '???',
      age: 0,
      university: '???대학교',
      department: '???학과',
      grade: 0,
      isMystery: true,
    ),
    MockUser(
      id: 'm2',
      name: '???',
      age: 0,
      university: '???대학교',
      department: '???학과',
      grade: 0,
      isMystery: true,
    ),
    MockUser(
      id: 'm3',
      name: '???',
      age: 0,
      university: '???대학교',
      department: '???학과',
      grade: 0,
      isMystery: true,
    ),
  ];

  // 현재 로그인 사용자
  static const MockUser currentUser = MockUser(
    id: 'me',
    name: '사용자 이름',
    nickname: '닉네임',
    age: 23,
    university: '성균관대학교',
    department: '소프트웨어학과',
    grade: 3,
    mbti: 'ENTP',
    height: 172,
    tags: ['개발', '음악', '맛집'],
    introduction: '안녕하세요! 반가워요 😊',
  );
}
