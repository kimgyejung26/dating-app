// =============================================================================
// 채팅방 화면
// 경로: lib/features/chat/screens/chat_room_screen.dart
// =============================================================================

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

import '../services/chat_service.dart';
import '../../../services/storage_service.dart';
import '../../../services/user_service.dart';

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
enum MessageType { received, sent }

class _ChatMessage {
  final MessageType type;
  final String text;
  final String time;
  final bool isRead;

  const _ChatMessage({
    required this.type,
    required this.text,
    required this.time,
    this.isRead = false,
  });
}

// =============================================================================
// 메인 화면
// =============================================================================
class ChatRoomScreen extends StatefulWidget {
  final String chatRoomId;
  final String partnerId;
  final String partnerName;
  final String partnerUniversity;
  final String? partnerAvatarUrl;
  final VoidCallback? onBack;
  final VoidCallback? onMore;
  final Function(String message)? onSend;

  const ChatRoomScreen({
    super.key,
    this.chatRoomId = '',
    this.partnerId = '',
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
  static const double _headerHeight = 120;

  final StorageService _storageService = StorageService();
  final UserService _userService = UserService();
  final ChatService _chatService = ChatService();
  final ScrollController _scrollController = ScrollController();

  String? _currentUserId;
  String _currentUserName = '나';
  String? _currentUserAvatarUrl;
  String _roomId = '';
  String? _initError;
  bool _isReady = false;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _initChat();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;

      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _initChat() async {
    try {
      final kakaoUserId = await _storageService.getKakaoUserId();

      if (kakaoUserId == null || kakaoUserId.isEmpty) return;
      debugPrint('CHAT kakaoUserId: $kakaoUserId');
      debugPrint('CHAT partnerId: ${widget.partnerId}');
      debugPrint('CHAT chatRoomId: ${widget.chatRoomId}');

      if (widget.partnerId.isEmpty) {
        throw Exception('partnerId 없음');
      }

      final user = await _userService.getUserProfile(kakaoUserId);
      final onboarding = user?['onboarding'];

      _currentUserId = kakaoUserId;
      _currentUserName = (onboarding is Map && onboarding['nickname'] != null)
          ? onboarding['nickname'].toString()
          : (user?['nickname']?.toString() ?? '나');
      String? resolvedAvatarUrl;

      if (onboarding is Map) {
        final photoUrlsRaw = onboarding['photoUrls'];
        if (photoUrlsRaw is List && photoUrlsRaw.isNotEmpty) {
          final firstPhoto = photoUrlsRaw.first?.toString() ?? '';
          if (firstPhoto.isNotEmpty) {
            resolvedAvatarUrl = firstPhoto;
          }
        }
      }

      resolvedAvatarUrl ??= user?['profileImageUrl']?.toString();

      _currentUserAvatarUrl = resolvedAvatarUrl;

      _roomId = _chatService.buildDirectRoomId(kakaoUserId, widget.partnerId);

      await _chatService.ensureDirectRoom(
        currentUserId: kakaoUserId,
        partnerId: widget.partnerId,
        currentUserName: _currentUserName,
        partnerName: widget.partnerName,
        currentUserAvatarUrl: _currentUserAvatarUrl,
        partnerAvatarUrl: widget.partnerAvatarUrl,
      );

      if (!mounted) return;
      setState(() {
        _isReady = true;
      });
    } catch (e) {
      debugPrint('CHAT INIT ERROR: $e');
      if (!mounted) return;
      setState(() {
        _isReady = false;
        _initError = e.toString();
      });
    }
  }

  Future<void> _handleSend() async {
    final text = _messageController.text.trim();
    if (text.isEmpty ||
        _currentUserId == null ||
        _roomId.isEmpty ||
        _isSending) {
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      _messageController.clear();

      await _chatService.sendTextMessage(
        roomId: _roomId,
        senderId: _currentUserId!,
        text: text,
      );

      widget.onSend?.call(text);
      _scrollToBottom();
    } finally {
      if (!mounted) return;
      setState(() {
        _isSending = false;
      });
    }
  }

  String _formatTime(dynamic ts) {
    if (ts is! Timestamp) return '';
    final dt = ts.toDate();
    final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
    final minute = dt.minute.toString().padLeft(2, '0');
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$minute $period';
  }

  _ChatMessage _mapMessage(Map<String, dynamic> data) {
    final senderId = data['senderId']?.toString() ?? '';
    final text = data['text']?.toString() ?? '';
    final ts = data['createdAt'];
    String timeText = '';

    if (ts is Timestamp) {
      final dt = ts.toDate();
      final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
      final minute = dt.minute.toString().padLeft(2, '0');
      final period = dt.hour >= 12 ? 'PM' : 'AM';
      timeText = '$hour:$minute $period';
    }

    return _ChatMessage(
      type: senderId == _currentUserId
          ? MessageType.sent
          : MessageType.received,
      text: text,
      time: timeText,
      isRead: senderId == _currentUserId,
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      child: Stack(
        children: [
          CustomScrollView(
            controller: _scrollController,
            physics: const BouncingScrollPhysics(),
            slivers: [
              SliverToBoxAdapter(child: SizedBox(height: _headerHeight)),
              SliverPadding(
                padding: EdgeInsets.fromLTRB(24, 12, 24, bottomPadding + 120),
                sliver: !_isReady
                    ? SliverToBoxAdapter(
                        child: Center(
                          child: Padding(
                            padding: const EdgeInsets.only(top: 40),
                            child: _initError == null
                                ? const CupertinoActivityIndicator()
                                : Text(
                                    '채팅방을 불러오지 못했어요\n$_initError',
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      fontFamily: 'Noto Sans KR',
                                      fontSize: 14,
                                      color: _AppColors.textSubtle,
                                    ),
                                  ),
                          ),
                        ),
                      )
                    : StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                        stream: _chatService.messagesStream(_roomId),
                        builder: (context, snapshot) {
                          if (snapshot.connectionState ==
                              ConnectionState.waiting) {
                            return const SliverToBoxAdapter(
                              child: Center(
                                child: Padding(
                                  padding: EdgeInsets.only(top: 40),
                                  child: CupertinoActivityIndicator(),
                                ),
                              ),
                            );
                          }

                          if (!snapshot.hasData) {
                            return const SliverToBoxAdapter(child: SizedBox());
                          }

                          final docs = snapshot.data!.docs;

                          if (docs.isEmpty) {
                            return const SliverToBoxAdapter(
                              child: Padding(
                                padding: EdgeInsets.only(top: 80),
                                child: Center(
                                  child: Text(
                                    '채팅을 시작해 보세요!',
                                    style: TextStyle(
                                      fontFamily: 'Noto Sans KR',
                                      fontSize: 15,
                                      color: _AppColors.textSubtle,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }

                          return SliverList(
                            delegate: SliverChildBuilderDelegate((
                              context,
                              index,
                            ) {
                              final data = docs[index].data();
                              final message = _mapMessage(data);

                              return _MessageItem(
                                message: message,
                                avatarUrl:
                                    widget.partnerAvatarUrl ??
                                    _defaultAvatarUrl,
                              );
                            }, childCount: docs.length),
                          );
                        },
                      ),
              ),
            ],
          ),
          Positioned(
            left: 0,
            right: 0,
            top: 0,
            child: _Header(
              name: widget.partnerName,
              university: widget.partnerUniversity,
              onBack: widget.onBack,
              onMore: widget.onMore,
            ),
          ),
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
            Column(
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        fontFamily: 'Noto Sans KR',
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
                          fontFamily: 'Noto Sans KR',
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
      case MessageType.received:
        return _ReceivedMessage(
          text: message.text,
          time: message.time,
          avatarUrl: avatarUrl,
        );
      case MessageType.sent:
        return _SentMessage(
          text: message.text,
          time: message.time,
          isRead: message.isRead,
        );
    }
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
                      fontFamily: 'Noto Sans KR',
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
                fontFamily: 'Noto Sans KR',
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
                fontFamily: 'Noto Sans KR',
                fontSize: 15,
                fontWeight: FontWeight.w400,
                height: 1.5,
                color: _AppColors.textMain,
              ),
            ),
          ),
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
                    fontFamily: 'Noto Sans KR',
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
            CupertinoButton(
              padding: EdgeInsets.zero,
              onPressed: () {},
              child: Transform.rotate(
                angle: 0.785,
                child: const Icon(
                  CupertinoIcons.paperclip,
                  size: 24,
                  color: _AppColors.stone400,
                ),
              ),
            ),
            Expanded(
              child: CupertinoTextField(
                controller: controller,
                placeholder: 'Write a message...',
                placeholderStyle: const TextStyle(
                  fontFamily: 'Noto Sans KR',
                  fontSize: 15,
                  color: _AppColors.stone400,
                ),
                style: const TextStyle(
                  fontFamily: 'Noto Sans KR',
                  fontSize: 15,
                  color: _AppColors.textMain,
                ),
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 12,
                ),
                decoration: null,
                onSubmitted: (_) => onSend?.call(),
              ),
            ),
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
