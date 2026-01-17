import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _verificationCodeController = TextEditingController();

  final FirebaseAuth _auth = FirebaseAuth.instance;

  bool _isVerificationSent = false;
  bool _isVerified = false;
  bool _isLoading = false;

  // 모바일용
  String? _verificationId;

  // 웹용
  ConfirmationResult? _confirmationResult;

  @override
  void dispose() {
    _phoneController.dispose();
    _verificationCodeController.dispose();
    super.dispose();
  }

  // 전화번호를 +82 E.164 형식으로 변환 (한국 번호 처리)
  String _formatPhoneNumber(String phone) {
    final digits = phone.replaceAll(RegExp(r'[^\d]'), '');

    if (digits.startsWith('010') && digits.length == 11) {
      return '+82${digits.substring(1)}'; // 010xxxxxxxx -> +8210xxxxxxxx
    }

    if (phone.trim().startsWith('+')) {
      return phone.trim();
    }

    if (digits.startsWith('82')) {
      return '+$digits';
    }

    return '+82$digits';
  }

  void _showSnack(String message, {Color? color}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: color,
      ),
    );
  }

  Future<void> _sendVerificationCode() async {
    final isValid = _formKey.currentState?.validate() ?? false;
    if (!isValid) return;

    setState(() => _isLoading = true);

    try {
      final phoneNumber = _formatPhoneNumber(_phoneController.text.trim());

      if (kIsWeb) {
        // ✅ 웹: 이 방식이 reCAPTCHA 처리에 가장 안정적
        _confirmationResult = await _auth.signInWithPhoneNumber(phoneNumber);

        if (!mounted) return;
        setState(() {
          _isVerificationSent = true;
          _isLoading = false;
        });
        _showSnack('인증번호가 전송되었습니다.', color: Colors.green);
        return;
      }

      // ✅ 모바일(Android/iOS): 기존 방식 유지
      await _auth.verifyPhoneNumber(
        phoneNumber: phoneNumber,

        verificationCompleted: (PhoneAuthCredential credential) async {
          try {
            await _auth.signInWithCredential(credential);
            if (!mounted) return;

            setState(() {
              _isVerified = true;
              _isLoading = false;
            });

            _showSnack('인증이 완료되었습니다!', color: Colors.green);
          } catch (e) {
            if (!mounted) return;
            setState(() => _isLoading = false);
            _showSnack('자동 인증 실패: $e', color: Colors.red);
          }
        },

        verificationFailed: (FirebaseAuthException e) {
          debugPrint('verifyPhoneNumber failed: code=${e.code}, message=${e.message}');
          if (!mounted) return;
          setState(() => _isLoading = false);

          final msg = e.message ?? e.code;
          _showSnack('인증번호 전송 실패: $msg', color: Colors.red);
        },

        codeSent: (String verificationId, int? resendToken) {
          if (!mounted) return;

          setState(() {
            _verificationId = verificationId;
            _isVerificationSent = true;
            _isLoading = false;
          });

          _showSnack('인증번호가 전송되었습니다.', color: Colors.green);
        },

        codeAutoRetrievalTimeout: (String verificationId) {
          _verificationId = verificationId;
        },

        timeout: const Duration(seconds: 60),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showSnack('오류 발생: $e', color: Colors.red);
    }
  }

  Future<void> _verifyCode() async {
    final code = _verificationCodeController.text.trim();

    if (!_isVerificationSent) {
      _showSnack('인증번호를 먼저 전송해주세요.', color: Colors.red);
      return;
    }

    if (code.isEmpty || code.length != 6) {
      _showSnack('6자리 인증번호를 입력해주세요.', color: Colors.red);
      return;
    }

    setState(() => _isLoading = true);

    try {
      if (kIsWeb) {
        // ✅ 웹: confirmationResult.confirm(code)
        final result = await _confirmationResult?.confirm(code);

        if (result?.user == null) {
          throw FirebaseAuthException(
            code: 'web-confirm-failed',
            message: '웹 인증에 실패했습니다(ConfirmationResult가 null이거나 user가 null).',
          );
        }

        if (!mounted) return;
        setState(() {
          _isVerified = true;
          _isLoading = false;
        });
        _showSnack('인증이 완료되었습니다!', color: Colors.green);
        return;
      }

      // ✅ 모바일: verificationId + smsCode
      if (_verificationId == null) {
        throw FirebaseAuthException(
          code: 'missing-verification-id',
          message: 'verificationId가 없습니다. 인증번호를 다시 받아주세요.',
        );
      }

      final credential = PhoneAuthProvider.credential(
        verificationId: _verificationId!,
        smsCode: code,
      );

      await _auth.signInWithCredential(credential);

      if (!mounted) return;

      if (_auth.currentUser != null) {
        setState(() {
          _isVerified = true;
          _isLoading = false;
        });
        _showSnack('인증이 완료되었습니다!', color: Colors.green);
      } else {
        setState(() => _isLoading = false);
        _showSnack('인증에 실패했습니다. 다시 시도해주세요.', color: Colors.red);
      }
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);

      String errorMessage;
      switch (e.code) {
        case 'invalid-verification-code':
          errorMessage = '인증번호가 올바르지 않습니다.';
          break;
        case 'session-expired':
          errorMessage = '인증 시간이 만료되었습니다. 다시 인증번호를 받아주세요.';
          break;
        default:
          errorMessage = '인증 실패: ${e.message ?? e.code}';
      }

      _showSnack(errorMessage, color: Colors.red);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showSnack('오류 발생: $e', color: Colors.red);
    }
  }

  @override
  Widget build(BuildContext context) {
    final canEditPhone = !_isVerificationSent && !_isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('계정 생성'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '계정을 생성해주세요',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 24),

              // Phone Number Input
              TextFormField(
                controller: _phoneController,
                decoration: const InputDecoration(
                  labelText: '휴대폰 번호',
                  hintText: '010-1234-5678 또는 +82 10-1234-5678',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
                enabled: canEditPhone,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '휴대폰 번호를 입력해주세요';
                  }
                  final digits = value.replaceAll(RegExp(r'[^\d]'), '');
                  if (digits.length < 10 || digits.length > 13) {
                    return '올바른 전화번호를 입력해주세요';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Verification Code Input
              if (_isVerificationSent) ...[
                TextFormField(
                  controller: _verificationCodeController,
                  decoration: const InputDecoration(
                    labelText: '인증번호',
                    hintText: '6자리 인증번호',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  enabled: !_isLoading,
                ),
                const SizedBox(height: 24),
              ] else ...[
                const SizedBox(height: 24),
              ],

              // Send Verification Button
              if (!_isVerificationSent)
                ElevatedButton(
                  onPressed: _isLoading ? null : _sendVerificationCode,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                      : const Text('인증번호 받기'),
                ),

              // Verify Button
              if (_isVerificationSent && !_isVerified)
                ElevatedButton(
                  onPressed: _isLoading ? null : _verifyCode,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                      : const Text('확인'),
                ),

              // Next Button
              if (_isVerified)
                ElevatedButton(
                  onPressed: () {
                    context.push('/student-verification');
                  },
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: const Text('다음'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
