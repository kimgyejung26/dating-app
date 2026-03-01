import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:uuid/uuid.dart';

import '../../../router/route_names.dart';
import '../../../services/auth_service.dart';
import '../../../services/storage_service.dart';
import '../../../utils/open_mail_app.dart';

class StudentVerificationScreen extends StatefulWidget {
  const StudentVerificationScreen({super.key});

  @override
  State<StudentVerificationScreen> createState() =>
      _StudentVerificationScreenState();
}

class _StudentVerificationScreenState extends State<StudentVerificationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _authService = AuthService();
  final _storageService = StorageService();

  bool _isSending = false;
  bool _isVerifying = false;
  String? _statusMessage;

  static const String _yonseiDomain = '@yonsei.ac.kr';

  String _buildYonseiEmail(String input) {
    final raw = input.trim().toLowerCase();
    if (raw.isEmpty) return '';

    // 사용자가 전체 이메일을 붙여넣어도 안전하게 처리
    final localPart = raw.contains('@') ? raw.split('@').first : raw;
    return '$localPart$_yonseiDomain';
  }

  Future<void> _showDialogMessage(String title, String message) async {
    if (!mounted) return;
    await showCupertinoDialog<void>(
      context: context,
      builder: (_) => CupertinoAlertDialog(
        title: Text(title),
        content: Text(message),
        actions: const [
          CupertinoDialogAction(child: Text('확인')),
        ],
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _prefillSavedEmail();
      _checkForEmailLink();
    });
  }

  Future<void> _prefillSavedEmail() async {
    final kakaoUserId = await _storageService.getKakaoUserId();
    if (kakaoUserId == null) return;

    final saved = await _storageService.getStudentEmail(kakaoUserId);
    if (saved == null || saved.trim().isEmpty) return;

    final localPart = saved.trim().toLowerCase().split('@').first;
    if (localPart.isEmpty) return;

    if (!mounted) return;
    setState(() => _emailController.text = localPart);
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  // Web에서 이메일 링크로 들어온 경우에만 동작 (native는 보통 브라우저에서 처리)
  Future<void> _checkForEmailLink() async {
    final link = Uri.base.toString();
    if (!_authService.isSignInWithEmailLink(link)) return;

    setState(() {
      _isVerifying = true;
      _statusMessage = '이메일 링크 인증을 완료하는 중...';
    });

    try {
      final kakaoUserId = await _storageService.getKakaoUserId();
      if (kakaoUserId == null) {
        throw Exception('카카오 로그인 정보가 없습니다.');
      }

      final savedEmail = (await _storageService.getStudentEmail(kakaoUserId) ?? '')
          .trim()
          .toLowerCase();
      final email = savedEmail.isNotEmpty
          ? savedEmail
          : _buildYonseiEmail(_emailController.text);

      if (email.isEmpty) {
        throw Exception('이메일 정보를 찾을 수 없습니다. 다시 시도해주세요.');
      }

      await _authService.signInWithEmailLink(email: email, emailLink: link);

      // Firestore에 학생 인증 기록 (기존 서비스 메서드 사용)
      await _authService.setStudentVerified(
        kakaoUserId: kakaoUserId,
        studentEmail: email,
      );

      if (!mounted) return;
      setState(() => _statusMessage = '학생 인증 완료!');
      Navigator.of(context).pushReplacementNamed(RouteNames.onboardingBasicInfo);
    } catch (e) {
      if (!mounted) return;
      setState(() => _statusMessage = '인증 실패: ${e.toString()}');
      await _showDialogMessage('인증 실패', e.toString());
    } finally {
      if (mounted) setState(() => _isVerifying = false);
    }
  }

  Future<void> _sendEmailLink() async {
    if (!_formKey.currentState!.validate()) return;

    final kakaoUserId = await _storageService.getKakaoUserId();
    if (kakaoUserId == null) {
      if (!mounted) return;
      await _showDialogMessage('전송 불가', '카카오 로그인 정보가 없습니다.');
      return;
    }

    final email = _buildYonseiEmail(_emailController.text);

    setState(() {
      _isSending = true;
      _statusMessage = '인증 링크를 전송하는 중...';
    });

    try {
      final token = const Uuid().v4();

      // 1) 토큰 문서 저장 (웹이 이걸 읽어서 email/kakaoUserId를 알아냄)
      await FirebaseFirestore.instance
          .collection('emailLinkTokens')
          .doc(token)
          .set({
        'email': email,
        'kakaoUserId': kakaoUserId,
        'createdAt': FieldValue.serverTimestamp(),
        'expiresAt': Timestamp.fromDate(
          DateTime.now().add(const Duration(minutes: 30)),
        ),
      });

      // 2) continueUrl에 토큰 붙이기 (핵심)
      final continueUrl = 'https://seolleyeon.web.app/auth/email-link?t=$token';

      // 3) Firebase 이메일 링크 전송
      await _authService.sendStudentEmailLink(email: email, continueUrl: continueUrl);

      // 4) 로컬에 이메일 저장 (웹 인증 후 앱에서 확인용)
      await _storageService.saveStudentEmail(kakaoUserId, email);
      await _storageService.setStudentVerified(kakaoUserId, false);

      if (!mounted) return;
      setState(() => _statusMessage = '연세 메일로 인증 링크를 보냈습니다');
    } catch (e, stack) {
      debugPrint('❌ 이메일 인증 링크 전송 실패');
      debugPrint(e.toString());
      debugPrint(stack.toString());

      if (!mounted) return;
      setState(() => _statusMessage = '전송 실패: ${e.toString()}');

      await _showDialogMessage('전송 실패', e.toString());
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  Future<void> _checkVerificationStatus() async {
    setState(() {
      _isVerifying = true;
      _statusMessage = '인증 상태를 확인하는 중...';
    });

    try {
      final kakaoUserId = await _storageService.getKakaoUserId();
      if (kakaoUserId == null) {
        throw Exception('카카오 로그인 정보가 없습니다.');
      }

      // ✅ 사용자가 이 기기에서 인증 링크를 보낸 적이 없으면 통과 불가
      final savedEmail = (await _storageService.getStudentEmail(kakaoUserId) ?? '')
          .trim()
          .toLowerCase();
      if (savedEmail.isEmpty) {
        if (!mounted) return;
        setState(() => _statusMessage = '❗ 아직 이메일 인증이 완료되지 않았습니다');
        return;
      }

      // Firestore에서 최신 학생 인증 상태 다시 조회
      final isVerified = await _authService.isStudentVerified(kakaoUserId);

      if (isVerified) {
        // ✅ Firestore에 저장된 이메일이 저장된 이메일과 일치할 때만 통과
        final firestoreEmail =
            (await _authService.getStudentEmail(kakaoUserId) ?? '')
                .trim()
                .toLowerCase();
        if (firestoreEmail.isEmpty || firestoreEmail != savedEmail) {
          if (!mounted) return;
          setState(() => _statusMessage = '❗ 아직 이메일 인증이 완료되지 않았습니다');
          return;
        }

        // 로컬에도 verified 기록 (다음 실행에서 UX 개선)
        await _storageService.setStudentVerified(kakaoUserId, true);

        if (!mounted) return;
        setState(() => _statusMessage = '학생 인증이 확인되었습니다!');
        HapticFeedback.mediumImpact();
        Navigator.of(context).pushReplacementNamed(RouteNames.onboardingBasicInfo);
        return;
      }

      if (!mounted) return;
      setState(() => _statusMessage = '❗ 아직 이메일 인증이 완료되지 않았습니다');
    } catch (e) {
      if (!mounted) return;
      setState(() => _statusMessage = '확인 실패: ${e.toString()}');
      await _showDialogMessage('확인 실패', e.toString());
    } finally {
      if (mounted) setState(() => _isVerifying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;

    return CupertinoPageScaffold(
      backgroundColor: _AppColors.backgroundLight,
      navigationBar: const CupertinoNavigationBar(
        middle: Text('연세 이메일 인증'),
      ),
      child: SafeArea(
        child: Stack(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 8),
                  const Text(
                    '연세대학교 이메일\n인증이 필요해요',
                    style: TextStyle(
                      fontFamily: '.SF Pro Display',
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      height: 1.25,
                      letterSpacing: -0.4,
                      color: _AppColors.textMain,
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    '@yonsei.ac.kr 메일로 인증 링크를 보내드릴게요.\n메일에서 인증을 완료한 뒤, 아래에서 확인을 눌러주세요.',
                    style: TextStyle(
                      fontFamily: '.SF Pro Text',
                      fontSize: 15,
                      height: 1.5,
                      color: _AppColors.textSub,
                    ),
                  ),
                  const SizedBox(height: 18),
                  Form(
                    key: _formKey,
                    child: Material(
                      color: Colors.transparent,
                      child: TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        decoration: InputDecoration(
                          labelText: '연세 메일 아이디',
                          hintText: 'example',
                          suffixText: _yonseiDomain,
                          filled: true,
                          fillColor: _AppColors.surfaceLight,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                            borderSide: const BorderSide(color: _AppColors.border),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                            borderSide: const BorderSide(color: _AppColors.border),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                            borderSide: const BorderSide(
                              color: _AppColors.primary,
                              width: 2,
                            ),
                          ),
                        ),
                        validator: (value) {
                          final raw = (value ?? '').trim().toLowerCase();
                          if (raw.isEmpty) return '아이디를 입력해주세요';

                          // 전체 이메일을 붙여넣는 케이스도 허용하되, 연세 도메인만 통과
                          if (raw.contains('@')) {
                            if (!raw.endsWith(_yonseiDomain)) {
                              return '연세 이메일만 가능합니다';
                            }
                          }

                          final local = raw.contains('@') ? raw.split('@').first : raw;
                          final isValidLocal = RegExp(r'^[a-z0-9._-]{2,}$').hasMatch(local);
                          if (!isValidLocal) return '아이디 형식을 확인해주세요';
                          return null;
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_statusMessage != null) ...[
                    Text(
                      _statusMessage!,
                      style: const TextStyle(
                        fontFamily: '.SF Pro Text',
                        fontSize: 13,
                        height: 1.35,
                        color: _AppColors.textSub,
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],
                  const Spacer(),
                  SizedBox(height: bottomPadding + 110), // 하단 버튼 영역 확보
                ],
              ),
            ),
            // Bottom actions
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                padding: EdgeInsets.fromLTRB(24, 14, 24, bottomPadding + 16),
                decoration: BoxDecoration(
                  color: _AppColors.backgroundLight.withValues(alpha: 0.96),
                  border: const Border(top: BorderSide(color: _AppColors.divider)),
                ),
                child: Column(
                  children: [
                    SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: CupertinoButton(
                        padding: EdgeInsets.zero,
                        borderRadius: BorderRadius.circular(28),
                        color: _AppColors.primary,
                        onPressed: _isSending ? null : _sendEmailLink,
                        child: _isSending
                            ? const CupertinoActivityIndicator(color: Colors.white)
                            : const Text(
                                '인증 링크 보내기',
                                style: TextStyle(
                                  fontFamily: '.SF Pro Text',
                                  fontSize: 17,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: CupertinoButton(
                              padding: EdgeInsets.zero,
                              borderRadius: BorderRadius.circular(14),
                              color: _AppColors.surfaceLight,
                              onPressed: () => openGmailApp(context),
                              child: const Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(CupertinoIcons.mail, size: 18, color: _AppColors.textMain),
                                  SizedBox(width: 6),
                                  Text(
                                    '메일 앱 열기',
                                    style: TextStyle(
                                      fontFamily: '.SF Pro Text',
                                      fontSize: 15,
                                      fontWeight: FontWeight.w600,
                                      color: _AppColors.textMain,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: CupertinoButton(
                              padding: EdgeInsets.zero,
                              borderRadius: BorderRadius.circular(14),
                              color: _AppColors.gray700,
                              onPressed: _isVerifying ? null : _checkVerificationStatus,
                              child: _isVerifying
                                  ? const CupertinoActivityIndicator(color: Colors.white)
                                  : const Text(
                                      '인증 완료 확인',
                                      style: TextStyle(
                                        fontFamily: '.SF Pro Text',
                                        fontSize: 15,
                                        fontWeight: FontWeight.w700,
                                        color: Colors.white,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (_isVerifying) ...[
                      const SizedBox(height: 10),
                      const CupertinoActivityIndicator(),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AppColors {
  static const Color primary = Color(0xFFFF6B8A);
  static const Color backgroundLight = Color(0xFFFAFAFA);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color textMain = Color(0xFF0F172A);
  static const Color textSub = Color(0xFF64748B);
  static const Color border = Color(0xFFE5E7EB);
  static const Color divider = Color(0xFFF0F0F0);
  static const Color gray700 = Color(0xFF374151);
}

