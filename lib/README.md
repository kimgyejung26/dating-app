# 설레연 (Seolle-yeon) - 데이팅 앱 프로젝트 구조

## 📁 프로젝트 구조

```
lib/
├── main.dart                 # 앱 진입점
├── routes/
│   └── app_router.dart      # GoRouter 기반 라우팅 설정
├── models/
│   ├── user_model.dart      # 사용자 모델
│   └── preference_model.dart # 선호도 모델
├── providers/
│   └── auth_provider.dart   # 인증 상태 관리 (Provider)
├── services/
│   ├── api_service.dart      # API 통신 서비스
│   ├── auth_service.dart    # 인증 서비스
│   └── storage_service.dart # 로컬 저장소 서비스
├── screens/
│   ├── auth/
│   │   ├── welcome_screen.dart           # 환영 화면
│   │   ├── terms_screen.dart             # 약관 동의 화면
│   │   ├── signup_screen.dart            # 계정 생성 화면
│   │   ├── student_verification_screen.dart # 재학생 인증 화면
│   │   └── initial_setup_screen.dart     # 초기 설정 화면
│   ├── tutorial/
│   │   └── tutorial_screen.dart         # 튜토리얼 화면
│   ├── main/
│   │   └── main_screen.dart              # 메인 화면 (하단 네비게이션)
│   ├── matching/
│   │   └── matching_screen.dart          # 설레연 (매칭) 화면
│   ├── chat/
│   │   └── chat_list_screen.dart         # 채팅 목록 화면
│   ├── event/
│   │   └── event_screen.dart             # 이벤트 화면
│   ├── community/
│   │   └── community_screen.dart         # 대나무숲 (커뮤니티) 화면
│   └── profile/
│       └── profile_screen.dart           # 내 페이지 화면
└── widgets/                               # 재사용 가능한 위젯들 (향후 추가)
```

## 🔄 앱 플로우

### 1. 인증 플로우
```
환영 화면 → 약관 동의 → 계정 생성 → 재학생 인증 → 초기 설정 → 튜토리얼 → 메인 화면
```

### 2. 메인 화면
- **설레연**: AI 기반 인연 추천
- **채팅**: 1:1 채팅, 3:3 채팅, 채팅 어시스턴트
- **이벤트**: 3:3 미팅, 제휴, 1:1 소모임
- **대나무숲**: 연애 관련 커뮤니티
- **내 페이지**: 프로필 관리, 설정, 머니 충전 등

## 📦 주요 패키지

- **provider**: 상태 관리
- **go_router**: 라우팅
- **shared_preferences**: 로컬 저장소
- **dio**: HTTP 클라이언트
- **image_picker**: 이미지 선택
- **cached_network_image**: 이미지 캐싱
- **intl**: 날짜/시간 포맷팅

## 🚀 다음 단계

1. **API 연동**: 실제 백엔드 API와 연동
2. **Firebase 연동**: 인증, 스토리지, 실시간 데이터베이스
3. **AI 매칭 로직**: 사용자 취향 기반 매칭 알고리즘
4. **결제 시스템**: 머니 충전 및 차감 로직
5. **실시간 채팅**: WebSocket 또는 Firebase를 이용한 채팅
6. **푸시 알림**: 매칭, 채팅 등 알림 기능
7. **이미지 업로드**: 프로필 사진 및 이미지 관리

## 📝 주요 기능 (다이어그램 기반)

### 인증
- ✅ 환영 메시지
- ✅ 약관 동의 (필수/선택)
- ✅ 계정 생성 (휴대폰 인증, 카카오톡 인증)
- ✅ 재학생 인증 (연세포탈)
- ✅ 초기 설정 (프로필, 선호도)

### 메인 기능
- ✅ 설레연 (AI 매칭)
- ✅ 채팅 (1:1, 3:3, 어시스턴트)
- ✅ 이벤트 (3:3 미팅, 제휴, 소모임)
- ✅ 대나무숲 (커뮤니티)
- ✅ 내 페이지 (프로필, 설정)

### 향후 구현
- ⏳ AI 사진 기반 취향 필터링
- ⏳ 실제 인연 추천 알고리즘
- ⏳ Slot machine 인터페이스
- ⏳ 랜덤 매칭
- ⏳ 머니 시스템
- ⏳ 3:3 미팅 예약 및 관리
- ⏳ 안전 도장 시스템
