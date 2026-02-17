// =============================================================================
// 채팅방 화면
// 경로: lib/features/chat/screens/chat_room_screen.dart
//
// 사용 예시:
// Navigator.push(
//   context,
//   CupertinoPageRoute(builder: (_) => const ChatRoomScreen()),
// );
// =============================================================================

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

// =============================================================================
// 색상 상수
// =============================================================================
class _AppColors {
  static const Color primary = Color(0xFF3B5443);
  static const Color backgroundLight = Color(0xFFFAFAF9);
  static const Color bubbleUser = Color(0xFFF5F2EE);
  static const Color bubblePartner = Color(0xFFF0F3F5);
  static const Color textMain = Color(0xFF201F1D);
  static const Color textSubtle = Color(0xFF868E96);
  static const Color stone100 = Color(0xFFF5F5F4);
  static const Color stone200 = Color(0xFFE7E5E4);
  static const Color stone400 = Color(0xFFA8A29E);
  static const Color sendButton = Color(0xFFFFB2C1);
}

// =============================================================================
// 메시지 모델
// =============================================================================
enum MessageType { received, sent, aiTip, dateDivider }

class _ChatMessage {
  final MessageType type;
  final String? text;
  final String? time;
  final String? avatarUrl;
  final bool isRead;

  const _ChatMessage({
    required this.type,
    this.text,
    this.time,
    this.avatarUrl,
    this.isRead = false,
  });
}

// =============================================================================
// 메인 화면
// =============================================================================
class ChatRoomScreen extends StatefulWidget {
  final String partnerName;
  final String partnerUniversity;
  final String? partnerAvatarUrl;
  final VoidCallback? onBack;
  final VoidCallback? onMore;
  final Function(String message)? onSend;

  const ChatRoomScreen({
    super.key,
    this.partnerName = 'Kim Min-jun',
    this.partnerUniversity = "Seoul Nat'l Univ",
    this.partnerAvatarUrl,
    this.onBack,
    this.onMore,
    this.onSend,
  });

  @override
  State<ChatRoomScreen> createState() => _ChatRoomScreenState();
}

class _ChatRoomScreenState extends State<ChatRoomScreen> {
  final TextEditingController _messageController = TextEditingController();

  static const String _defaultAvatarUrl =
      'https://lh3.googleusercontent.com/aida-public/AB6AXuBbzHXe44kKkm38LFzZYDrJgB6VdcFI1wOqXLhzmXLluq6QpZFzdN4Kwf2jgvTVY0ulkwDXqpPKoaA8SnoMT5qhSFFGurIjc409LZqO6cs9LiNr2XWRHXHTIQhT0_trL5o9o3NSs5xIr8H1FtojhKTzR0P0wp5-9pIeGcdDl9D6vK5Fxv6IA8lfddlamHK7vlvzUfH7SNwgZ7OBgfMReB4O7jfppVehNPNaM5xl6dsuqMZKa2J3QbWJdkCeYQ20949IQZKdQuyh5Iqz';

  static const List<_ChatMessage> _messages = [
    _ChatMessage(type: MessageType.dateDivider, text: 'Today'),
    _ChatMessage(
      type: MessageType.received,
      text:
          'Have you finished your midterms yet? The library was so crowded today.',
      time: '14:20 PM',
      avatarUrl: _defaultAvatarUrl,
    ),
    _ChatMessage(
      type: MessageType.sent,
      text: 'Almost! Just one more paper to go. I need a coffee break badly ☕️',
      time: '14:22 PM',
      isRead: true,
    ),
    _ChatMessage(
      type: MessageType.aiTip,
      text:
          'Tip: Ask about their favorite study spot to keep the conversation flowing naturally.',
    ),
    _ChatMessage(
      type: MessageType.received,
      text: 'I know a great quiet cafe near campus. We should go sometime.',
      time: '14:24 PM',
      avatarUrl: _defaultAvatarUrl,
    ),
  ];

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  void _handleSend() {
    final text = _messageController.text.trim();
    if (text.isNotEmpty) {
      widget.onSend?.call(text);
      _messageController.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: Stack(
        children: [
          // 메시지 리스트
          CustomScrollView(
            physics: const BouncingScrollPhysics(),
            slivers: [
              // 헤더
              SliverToBoxAdapter(
                child: _Header(
                  name: widget.partnerName,
                  university: widget.partnerUniversity,
                  onBack: widget.onBack,
                  onMore: widget.onMore,
                ),
              ),
              // 메시지 리스트
              SliverPadding(
                padding: EdgeInsets.fromLTRB(24, 8, 24, bottomPadding + 120),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate((context, index) {
                    final message = _messages[index];
                    return _MessageItem(
                      message: message,
                      avatarUrl: widget.partnerAvatarUrl ?? _defaultAvatarUrl,
                    );
                  }, childCount: _messages.length),
                ),
              ),
            ],
          ),
          // 입력창
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _InputBar(
              controller: _messageController,
              bottomPadding: bottomPadding,
              onSend: _handleSend,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 헤더
// =============================================================================
class _Header extends StatelessWidget {
  final String name;
  final String university;
  final VoidCallback? onBack;
  final VoidCallback? onMore;

  const _Header({
    required this.name,
    required this.university,
    this.onBack,
    this.onMore,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 16),
        decoration: BoxDecoration(
          color: _AppColors.backgroundLight.withValues(alpha: 0.9),
          border: Border(bottom: BorderSide(color: _AppColors.stone100)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // 뒤로가기
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {
                HapticFeedback.lightImpact();
                if (onBack != null) {
                  onBack!();
                } else {
                  Navigator.of(context).pop();
                }
              },
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _AppColors.stone100,
                ),
                child: const Icon(
                  CupertinoIcons.back,
                  size: 24,
                  color: _AppColors.textMain,
                ),
              ),
            ),
            // 프로필 정보
            Column(
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        fontFamily: '.SF Pro Display',
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.3,
                        color: _AppColors.textMain,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: _AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _AppColors.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        CupertinoIcons.building_2_fill,
                        size: 14,
                        color: _AppColors.primary,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        university,
                        style: const TextStyle(
                          fontFamily: '.SF Pro Text',
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.3,
                          color: _AppColors.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            // 더보기
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: onMore,
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _AppColors.stone100,
                ),
                child: const Icon(
                  CupertinoIcons.ellipsis,
                  size: 24,
                  color: _AppColors.textMain,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// 메시지 아이템
// =============================================================================
class _MessageItem extends StatelessWidget {
  final _ChatMessage message;
  final String avatarUrl;

  const _MessageItem({required this.message, required this.avatarUrl});

  @override
  Widget build(BuildContext context) {
    switch (message.type) {
      case MessageType.dateDivider:
        return _DateDivider(text: message.text ?? '');
      case MessageType.received:
        return _ReceivedMessage(
          text: message.text ?? '',
          time: message.time ?? '',
          avatarUrl: avatarUrl,
        );
      case MessageType.sent:
        return _SentMessage(
          text: message.text ?? '',
          time: message.time ?? '',
          isRead: message.isRead,
        );
      case MessageType.aiTip:
        return _AiTipCard(text: message.text ?? '');
    }
  }
}

// =============================================================================
// 날짜 구분선
// =============================================================================
class _DateDivider extends StatelessWidget {
  final String text;

  const _DateDivider({required this.text});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          decoration: BoxDecoration(
            color: CupertinoColors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: _AppColors.stone100),
            boxShadow: [
              BoxShadow(
                color: CupertinoColors.black.withValues(alpha: 0.02),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
            ],
          ),
          child: Text(
            text,
            style: const TextStyle(
              fontFamily: '.SF Pro Text',
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: _AppColors.textSubtle,
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// 받은 메시지
// =============================================================================
class _ReceivedMessage extends StatelessWidget {
  final String text;
  final String time;
  final String avatarUrl;

  const _ReceivedMessage({
    required this.text,
    required this.time,
    required this.avatarUrl,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // 아바타
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _AppColors.stone200,
                  boxShadow: [
                    BoxShadow(
                      color: CupertinoColors.black.withValues(alpha: 0.05),
                      blurRadius: 4,
                    ),
                  ],
                ),
                clipBehavior: Clip.antiAlias,
                child: Image.network(
                  avatarUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const Icon(
                    CupertinoIcons.person_fill,
                    size: 20,
                    color: _AppColors.stone400,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              // 버블
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 14,
                  ),
                  decoration: BoxDecoration(
                    color: _AppColors.bubblePartner,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(20),
                      topRight: Radius.circular(20),
                      bottomRight: Radius.circular(20),
                      bottomLeft: Radius.circular(4),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: CupertinoColors.black.withValues(alpha: 0.04),
                        blurRadius: 2,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                  child: Text(
                    text,
                    style: const TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 15,
                      fontWeight: FontWeight.w400,
                      height: 1.5,
                      color: _AppColors.textMain,
                    ),
                  ),
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(left: 48, top: 4),
            child: Text(
              time,
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 10,
                color: _AppColors.stone400,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// 보낸 메시지
// =============================================================================
class _SentMessage extends StatelessWidget {
  final String text;
  final String time;
  final bool isRead;

  const _SentMessage({
    required this.text,
    required this.time,
    this.isRead = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // 버블
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: _AppColors.bubbleUser,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(20),
                topRight: Radius.circular(20),
                bottomLeft: Radius.circular(20),
                bottomRight: Radius.circular(4),
              ),
              border: Border.all(color: const Color(0xFFEFECE8)),
              boxShadow: [
                BoxShadow(
                  color: CupertinoColors.black.withValues(alpha: 0.04),
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: Text(
              text,
              style: const TextStyle(
                fontFamily: '.SF Pro Text',
                fontSize: 15,
                fontWeight: FontWeight.w400,
                height: 1.5,
                color: _AppColors.textMain,
              ),
            ),
          ),
          // 시간 & 읽음
          Padding(
            padding: const EdgeInsets.only(top: 4, right: 4),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isRead)
                  const Icon(
                    CupertinoIcons.checkmark_alt_circle_fill,
                    size: 12,
                    color: _AppColors.primary,
                  ),
                if (isRead) const SizedBox(width: 4),
                Text(
                  time,
                  style: const TextStyle(
                    fontFamily: '.SF Pro Text',
                    fontSize: 10,
                    color: _AppColors.stone400,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// AI 팁 카드
// =============================================================================
class _AiTipCard extends StatelessWidget {
  final String text;

  const _AiTipCard({required this.text});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.85,
          ),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFF8F5F2), Color(0xFFFFFCF9)],
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: _AppColors.stone100),
            boxShadow: [
              BoxShadow(
                color: CupertinoColors.black.withValues(alpha: 0.02),
                blurRadius: 4,
              ),
            ],
          ),
          child: Stack(
            children: [
              // 왼쪽 액센트 바
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                child: Container(
                  width: 4,
                  decoration: BoxDecoration(
                    color: _AppColors.primary.withValues(alpha: 0.3),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(16),
                      bottomLeft: Radius.circular(16),
                    ),
                  ),
                ),
              ),
              // 콘텐츠
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: _AppColors.primary.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        CupertinoIcons.sparkles,
                        size: 14,
                        color: _AppColors.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'AI ASSISTANT',
                            style: TextStyle(
                              fontFamily: '.SF Pro Text',
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1,
                              color: _AppColors.primary.withValues(alpha: 0.7),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            text,
                            style: const TextStyle(
                              fontFamily: '.SF Pro Text',
                              fontSize: 12,
                              height: 1.5,
                              color: _AppColors.textMain,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// 입력창
// =============================================================================
class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final double bottomPadding;
  final VoidCallback? onSend;

  const _InputBar({
    required this.controller,
    required this.bottomPadding,
    this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(16, 16, 16, bottomPadding + 32),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _AppColors.backgroundLight.withValues(alpha: 0),
            _AppColors.backgroundLight.withValues(alpha: 0.9),
            _AppColors.backgroundLight,
          ],
        ),
      ),
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 4, 8, 4),
        decoration: BoxDecoration(
          color: CupertinoColors.white,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: _AppColors.stone100),
          boxShadow: [
            BoxShadow(
              color: _AppColors.primary.withValues(alpha: 0.08),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            // 첨부 버튼
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {},
              child: Transform.rotate(
                angle: 0.785, // 45도
                child: const Icon(
                  CupertinoIcons.paperclip,
                  size: 24,
                  color: _AppColors.stone400,
                ),
              ),
            ),
            // 입력 필드
            Expanded(
              child: CupertinoTextField(
                controller: controller,
                placeholder: 'Write a message...',
                placeholderStyle: const TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 15,
                  color: _AppColors.stone400,
                ),
                style: const TextStyle(
                  fontFamily: '.SF Pro Text',
                  fontSize: 15,
                  color: _AppColors.textMain,
                ),
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 12,
                ),
                decoration: null,
              ),
            ),
            // 전송 버튼
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {
                HapticFeedback.mediumImpact();
                onSend?.call();
              },
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _AppColors.sendButton,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: _AppColors.sendButton.withValues(alpha: 0.4),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  CupertinoIcons.paperplane_fill,
                  size: 20,
                  color: CupertinoColors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
