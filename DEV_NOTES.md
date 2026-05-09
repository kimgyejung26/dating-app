# 설레연 Development Notes

## Project Overview
설레연 (Seol-le-yeon) is a university-focused dating application built with Flutter. This document serves as a technical reference for developers working on the front-end implementation.

## Design System

### Colors (`lib/design_system/seol_colors.dart`)
- **Primary**: Coral Pink (`#FF6B7A`) - Main brand color
- **Secondary**: Soft Purple (`#A78BFA`) - Supporting accent color
- **Background**: Subtle gradient of white with light pink/purple

### Typography (`lib/design_system/seol_typography.dart`)
- Font Family: Pretendard (Korean-optimized)
- Scales from `caption` (12px) to `h1` (32px)

### Components
| Component | File | Purpose |
|-----------|------|---------|
| `SeolButton` | `seol_button.dart` | Primary/secondary/text buttons with variants |
| `SeolCard` | `seol_card.dart` | Cards for profiles, posts |
| `SeolChip` | `seol_chip.dart` | Tags, filters, filter tabs |
| `SeolAppBar` | `seol_app_bar.dart` | Main app bar with notification |
| `SeolScaffold` | `seol_scaffold.dart` | Themed scaffold wrapper |
| `SeolBottomNav` | `seol_bottom_nav.dart` | 5-tab navigation |
| `SeolBottomSheet` | `seol_bottom_sheet.dart` | Modals, action sheets, confirmations |

## Routing

Routes are defined in `lib/routes/app_router.dart` using go_router.

### Auth Flow
```
/welcome → /terms → /auth-choice → /phone-auth OR /kakao-auth → /student-verification → /initial-setup → /tutorial → /main
```

### Main Tabs
- `/main` - Container with bottom navigation
- Tab 0: 설레연 (Matching)
- Tab 1: 채팅 (Chat)
- Tab 2: 이벤트 (Event/3:3)
- Tab 3: 대나무숲 (Community)
- Tab 4: 내 페이지 (Profile)

## Mock Data

All mock data is in `lib/mock/`:
- `mock_users.dart` - Sample user profiles, mystery users
- `mock_chats.dart` - Chat rooms, messages, AI assistant
- `mock_posts.dart` - Community posts with tags

## API Integration Points

All API calls are marked with `// TODO:` comments. Key integration points:

### Authentication
- `phone_auth_screen.dart`: Phone verification API
- `kakao_auth_screen.dart`: Kakao OAuth integration
- `student_verification_screen.dart`: University email verification

### Matching
- `matching_screen.dart`: Fetch daily matches from AI
- `profile_detail_screen.dart`: Like/pass actions

### Chat
- `chat_list_screen.dart`: Real-time chat list
- `chat_detail_screen.dart`: Message send/receive

### Community
- `community_screen.dart`: Fetch/filter posts
- Post creation, like, comment actions

## 3:3 Matching Rules
1. Single participation allowed (1명 혼자도 참여 가능)
2. All 6 participants must be strangers (6명은 모두 모르는 사람)
3. No-face participation is default (노페이스 참여가 기본)

## Running the App

```bash
# Development
flutter run -d chrome

# Build web
flutter build web --no-tree-shake-icons

# Analyze
flutter analyze lib/
```

## Current Implementation Status

- ✅ Design System Components
- ✅ Onboarding Flow (8 screens)
- ✅ Main Tab Navigation
- ✅ Community Screen
- ⏳ 3:3 Matching Flow (Phase 4)
- ⏳ My Page Sub-screens (Phase 5)
