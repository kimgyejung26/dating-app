import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../../services/storage_service.dart';
import '../../utils/open_mail_app.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:uuid/uuid.dart';

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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkForEmailLink();
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _checkForEmailLink() async {
    final link = Uri.base.toString();
    if (!_authService.isSignInWithEmailLink(link)) return;

    setState(() {
      _isVerifying = true;
      _statusMessage = '이메일 링크 인증을 완료하는 중...';
    });

    try {
      final authProvider = context.read<AuthProvider>();
      final kakaoUserId = authProvider.kakaoUserId;
      if (kakaoUserId == null) {
        throw Exception('카카오 로그인 정보가 없습니다.');
      }

      final savedEmail =
          await _storageService.getStudentEmail(kakaoUserId) ??
          _emailController.text.trim();
      if (savedEmail.isEmpty) {
        throw Exception('이메일 정보를 찾을 수 없습니다. 다시 시도해주세요.');
      }

      await _authService.signInWithEmailLink(
        email: savedEmail,
        emailLink: link,
      );

      await authProvider.setStudentVerified(savedEmail);

      if (!mounted) return;
      setState(() => _statusMessage = '학생 인증 완료!');
      context.go('/initial-setup');
    } catch (e) {
      if (!mounted) return;
      setState(() => _statusMessage = '인증 실패: ${e.toString()}');
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('인증 실패: ${e.toString()}')));
    } finally {
      if (mounted) {
        setState(() => _isVerifying = false);
      }
    }
  }

  Future<void> _sendEmailLink() async {
    if (!_formKey.currentState!.validate()) return;

    final authProvider = context.read<AuthProvider>();
    final kakaoUserId = authProvider.kakaoUserId;
    if (kakaoUserId == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('카카오 로그인 정보가 없습니다.')));
      return;
    }

    final email = _emailController.text.trim();

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
      await _authService.sendStudentEmailLink(
        email: email,
        continueUrl: continueUrl,
      );

      // 4) 로컬에 이메일 저장 (웹 인증 후 앱에서 확인용)
      await _storageService.saveStudentEmail(kakaoUserId, email);
      await _storageService.setStudentVerified(kakaoUserId, false);

      if (!mounted) return;

      setState(() {
        _statusMessage = '인증 링크가 전송되었습니다. 메일을 확인해주세요.';
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('연세 이메일로 인증 링크를 보냈습니다.')));
    } catch (e, stack) {
      debugPrint('❌ 이메일 인증 링크 전송 실패');
      debugPrint(e.toString());
      debugPrint(stack.toString());

      if (!mounted) return;

      setState(() {
        _statusMessage = '전송 실패: ${e.toString()}';
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('인증 링크 전송 실패: ${e.toString()}')));
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }

  Future<void> _checkVerificationStatus() async {
    setState(() {
      _isVerifying = true;
      _statusMessage = '인증 상태를 확인하는 중...';
    });

    try {
      final authProvider = context.read<AuthProvider>();
      final kakaoUserId = authProvider.kakaoUserId;

      if (kakaoUserId == null) {
        throw Exception('카카오 로그인 정보가 없습니다.');
      }

      // 🔥 Firestore에서 최신 학생 인증 상태 다시 조회
      final isVerified = await _authService.isStudentVerified(kakaoUserId);

      if (isVerified) {
        // Provider 상태도 최신화
        final email =
            await _authService.getStudentEmail(kakaoUserId) ??
            await _storageService.getStudentEmail(kakaoUserId);

        if (email != null) {
          await authProvider.setStudentVerified(email);
        }

        if (!mounted) return;
        setState(() => _statusMessage = '학생 인증이 확인되었습니다!');
        context.go('/initial-setup');
      } else {
        if (!mounted) return;
        setState(() => _statusMessage = '아직 이메일 인증이 완료되지 않았습니다.');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('아직 인증이 완료되지 않았습니다. 메일을 확인해주세요.')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _statusMessage = '확인 실패: ${e.toString()}');
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('확인 실패: ${e.toString()}')));
    } finally {
      if (mounted) {
        setState(() => _isVerifying = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('연세 이메일 인증')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '연세대학교 이메일(@yonsei.ac.kr) 인증',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: '연세 이메일',
                  hintText: 'example@yonsei.ac.kr',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '이메일을 입력해주세요';
                  }
                  final email = value.trim().toLowerCase();
                  if (!email.endsWith('@yonsei.ac.kr')) {
                    return '연세 이메일(@yonsei.ac.kr)만 가능합니다';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              if (_statusMessage != null) ...[
                Text(
                  _statusMessage!,
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),
                const SizedBox(height: 16),
              ],
              ElevatedButton(
                onPressed: _isSending ? null : _sendEmailLink,
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                ),
                child: _isSending
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('인증 링크 보내기'),
              ),

              ElevatedButton.icon(
                onPressed: () => openGmailApp(context),
                icon: const Icon(Icons.mail_outline),
                label: const Text('메일 앱 열기'),
              ),

              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _isVerifying ? null : _checkVerificationStatus,
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                  backgroundColor: Colors.grey.shade700,
                ),
                child: _isVerifying
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('인증 완료 확인'),
              ),

              const SizedBox(height: 16),
              if (_isVerifying)
                const Center(child: CircularProgressIndicator()),
            ],
          ),
        ),
      ),
    );
  }
}
