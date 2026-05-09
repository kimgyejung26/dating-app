# UI 플로우 (ui.drawio.html 기준)

`docs/ui.drawio.html`은 Draw.io(diagrams.net)로 작성된 설레연 앱 UI 플로우 다이어그램입니다.  
`docs/ui.drawio.svg`는 동일한 다이어그램의 SVG 형식입니다.  
브라우저에서 열어 보시거나, [diagrams.net](https://app.diagrams.net/)에서 **파일 → 열기**로 불러올 수 있습니다.

---

## 다이어그램 구조 요약

### 1. 진입점
- **환영 메시지** → 기존 회원 여부 **YES / NO**
  - **NO** → **회원가입 유도** (기본 정보 입력 단계)
  - **YES** → **로그인 유도** (소셜/카카오 로그인, 매칭부스 로그인 확인 등)

### 2. 회원가입 / 온보딩
- **기본 정보 입력 단계**
- **약관 동의** → **본인 인증** → **성별 선택**
- **소셜 로그인** / **카카오 로그인**
- **매칭부스 로그인 확인** (연세 로그인 검증)

### 3. 메인 앱 (하단 탭)
| 탭 | 다이어그램 요소 | 현재 구현 |
|----|-----------------|-----------|
| 설레연 | **스와이프** (AI 매칭 카드, Like, Pass) | `MatchingScreen` |
| 채팅 | **메시지 함** · 1:1 · 3:3 · **AI 추천 캐릭터** | `ChatListScreen` |
| 이벤트 | **스포츠/콘서트** (3:3, 이벤트) | `EventScreen` |
| 대나무숲 | **Q&A**, **컨텐츠** | `CommunityScreen` |
| 내 페이지 | **프로필** · **키워드** (나이, 키, MBTI 등) | `ProfileScreen` |

### 4. 기타 화면
- **튜토리얼** (앱 사용법)
- **채팅방** (1:1 / 3:3)
- **프로필 상세** (다른 사용자 프로필)
- **알림** 등

---

## 라우트 매핑

| 경로 | 화면 | 비고 |
|------|------|------|
| `/welcome` | `WelcomeScreen` | 환영 메시지, 시작하기 |
| `/terms` | `TermsScreen` | 약관 동의 |
| `/signup` | `SignupScreen` | 회원가입 |
| `/student-verification` | `StudentVerificationScreen` | 본인(연세) 인증 |
| `/initial-setup` | `InitialSetupScreen` | 기본 정보/성별 등 |
| `/tutorial` | `TutorialScreen` | 튜토리얼 |
| `/main` | `MainScreen` | 메인 (하단 탭) |

---

## 다이어그램 활용

- **기획/개발 시**: `ui.drawio.html`을 열어 화면 전환·기능 범위 확인
- **구현 정합성**: 위 표를 참고해 라우트·스크린과 다이어그램을 맞추어 개발

추가로 반영하고 싶은 화면이나 플로우가 있으면 알려 주세요.
