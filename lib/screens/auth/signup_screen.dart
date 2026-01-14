import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _verificationCodeController = TextEditingController();
  bool _isVerificationSent = false;
  bool _isVerified = false;

  @override
  void dispose() {
    _phoneController.dispose();
    _verificationCodeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('계정 생성'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '계정을 생성해주세요',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              
              // Phone Number Input
              TextFormField(
                controller: _phoneController,
                decoration: const InputDecoration(
                  labelText: '휴대폰 번호',
                  hintText: '010-1234-5678',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '휴대폰 번호를 입력해주세요';
                  }
                  return null;
                },
                enabled: !_isVerificationSent,
              ),
              const SizedBox(height: 16),
              
              // Verification Code Input
              if (_isVerificationSent)
                TextFormField(
                  controller: _verificationCodeController,
                  decoration: const InputDecoration(
                    labelText: '인증번호',
                    hintText: '6자리 인증번호',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return '인증번호를 입력해주세요';
                    }
                    return null;
                  },
                ),
              const SizedBox(height: 24),
              
              // Send Verification Button
              if (!_isVerificationSent)
                ElevatedButton(
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      // TODO: Send verification code
                      setState(() {
                        _isVerificationSent = true;
                      });
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: const Text('인증번호 전송'),
                ),
              
              // Verify Button
              if (_isVerificationSent && !_isVerified)
                ElevatedButton(
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      // TODO: Verify code
                      setState(() {
                        _isVerified = true;
                      });
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: const Text('인증번호 확인'),
                ),
              
              // Error Message
              if (_isVerificationSent && !_isVerified)
                const Padding(
                  padding: EdgeInsets.only(top: 16.0),
                  child: Text(
                    '계정을 생성하는 도중 문제가 발생했습니다. 인증이 완료되었는지 확인해주세요.',
                    style: TextStyle(
                      color: Colors.orange,
                      fontSize: 12,
                    ),
                  ),
                ),
              
              // Next Button
              if (_isVerified)
                ElevatedButton(
                  onPressed: () {
                    // TODO: Create account
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
