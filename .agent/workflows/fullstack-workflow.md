---
description: 설레연 데이팅 앱 풀스택 (프론트엔드 + 백엔드) 워크플로우
---

# 풀스택 워크플로우 (프론트엔드 + 백엔드)

이 워크플로우는 프론트엔드와 백엔드 모두를 포함한 전체 시스템 설계 흐름입니다.

## 1. 회원가입 및 로그인 흐름 (Backend 연동)

```
앱 시작 → 로그인 여부 확인
├── JWT 토큰 검증 (Backend)
│   ├── 유효 → 메인 화면
│   └── 만료 → 토큰 갱신 시도
│       ├── 성공 → 메인 화면
│       └── 실패 → 로그인 화면
└── 로그인 화면
    └── 휴대폰 번호 입력
        → SMS 인증 (외부 API: 알리고/NHN Toast)
        → 인증 완료 → DB 조회
            ├── 기존 회원 → 토큰 발급 → 메인
            └── 신규 회원 → 온보딩 시작
```

## 2. 온보딩 프로필 설정 (Data Flow)

### Frontend → Backend API 호출

| 단계 | Frontend | Backend API | DB Table |
|------|----------|-------------|----------|
| 이름 | TextInput | POST /api/user/name | users.name |
| 성별 | ToggleButton | POST /api/user/gender | users.gender |
| 생년월일 | DatePicker | POST /api/user/birthdate | users.birthdate |
| 키 | NumberInput | POST /api/user/height | users.height |
| 대학교 | SearchSelect | POST /api/user/university | users.university_id |
| 학생증 | ImageUpload | POST /api/verification/student | verifications |
| 학과 | TextInput | POST /api/user/major | users.major |
| MBTI | SelectGrid | POST /api/user/mbti | users.mbti |
| 지역 | LocationPicker | POST /api/user/location | users.location |
| 사진 | MultiImageUpload | POST /api/user/photos | user_photos |

### 학생증 인증 플로우
```
사진 업로드 → OCR 처리 (외부 API)
            → 텍스트 추출 (학교명, 학번, 이름)
            → DB 검증
                ├── 일치 → 인증 완료
                └── 불일치 → 수동 검토 대기
```

## 3. 메인 5개 탭 화면 (API 구조)

### 3.1 홈/매칭 (MatchingScreen)

**API Endpoints:**
- `GET /api/matching/recommendations` - 오늘의 추천 목록
- `POST /api/matching/like/{userId}` - 좋아요
- `POST /api/matching/pass/{userId}` - 패스
- `POST /api/matching/superlike/{userId}` - 슈퍼라이크

**매칭 알고리즘:**
```
추천 점수 = 
  (거리 점수 * 0.3) +
  (대학 랭크 유사도 * 0.2) +
  (MBTI 궁합 * 0.15) +
  (나이 선호도 * 0.15) +
  (관심사 일치도 * 0.2)
```

### 3.2 채팅 (ChatScreen)

**API Endpoints:**
- `GET /api/chat/rooms` - 채팅방 목록
- `GET /api/chat/rooms/{roomId}/messages` - 메시지 목록
- `POST /api/chat/rooms/{roomId}/messages` - 메시지 전송
- `WebSocket /ws/chat/{roomId}` - 실시간 채팅

**3:3 그룹 채팅:**
```
그룹 생성 요청 → 파티 구성
              → 매칭 대기열 등록
              → 상대 파티 매칭 완료
              → 그룹 채팅방 생성
```

### 3.3 커뮤니티 (CommunityScreen)

**API Endpoints:**
- `GET /api/community/posts` - 게시글 목록
- `POST /api/community/posts` - 게시글 작성
- `POST /api/community/posts/{id}/comments` - 댓글
- `POST /api/community/reports` - 신고

**신고 처리 플로우:**
```
신고 접수 → 자동 필터링 (욕설/스팸)
         → 관리자 검토 대기열
         → 처리 결과 알림
```

### 3.4 마이페이지 (MyPageScreen)

**API Endpoints:**
- `GET /api/user/profile` - 내 프로필
- `PUT /api/user/profile` - 프로필 수정
- `GET /api/user/points` - 매력 포인트
- `GET /api/user/matches/history` - 매칭 히스토리

### 3.5 더보기 (MoreScreen)

**API Endpoints:**
- `PUT /api/user/lifestyle` - 라이프스타일 설정
- `GET /api/subscription/status` - 구독 상태
- `POST /api/subscription/purchase` - 구독 결제

## 4. "우리 같이 약속해요" (서비스 규칙)

### 가입 전 약속사항
- 설레연에 가입하면 설정한 학교 학생에게만 프로필이 보입니다
- 같은 학교 보다 다른 학교 친구를 만나고 싶은 분들이 이용합니다
- 혼인 관계/연인이 있으신 분은 이용하실 수 없습니다

### 서비스 이용 약속
- ✓ 가짜가 아닌 정직한 정보로 이용하겠습니다
- ✓ 요청하지 않는 콘텐츠는 보내지 않겠습니다
- ✓ 다른 사람 사진이나 가짜 정보로 프로필을 작성하면 이용 제한될 수 있습니다
- ✓ 지인, 상대방의 동의 없이 사진을 외부로 유출하는 등의 피해를 주지 않겠습니다

### 위반 시 제재
- 경고 → 일시정지 → 영구정지 순으로 제재

## 5. 데이터베이스 스키마 (주요 테이블)

```sql
-- 사용자
CREATE TABLE users (
  id UUID PRIMARY KEY,
  phone VARCHAR(20) UNIQUE,
  name VARCHAR(50),
  gender ENUM('M', 'F'),
  birthdate DATE,
  height INT,
  university_id INT REFERENCES universities(id),
  major VARCHAR(100),
  mbti VARCHAR(4),
  location POINT,
  created_at TIMESTAMP
);

-- 프로필 사진
CREATE TABLE user_photos (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  photo_url VARCHAR(255),
  order_index INT,
  is_primary BOOLEAN
);

-- 매칭
CREATE TABLE matches (
  id UUID PRIMARY KEY,
  user1_id UUID REFERENCES users(id),
  user2_id UUID REFERENCES users(id),
  status ENUM('pending', 'matched', 'unmatched'),
  matched_at TIMESTAMP
);

-- 채팅방
CREATE TABLE chat_rooms (
  id UUID PRIMARY KEY,
  type ENUM('1:1', '3:3'),
  created_at TIMESTAMP
);
```

## 참고 이미지

원본 워크플로우 다이어그램:
![풀스택 워크플로우](C:/Users/samsung/.gemini/antigravity/brain/b4025e8d-be6e-464d-9cf0-295d6a0e2164/uploaded_media_1_1769664426566.png)
