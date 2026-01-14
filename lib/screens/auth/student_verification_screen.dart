import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class StudentVerificationScreen extends StatefulWidget {
  const StudentVerificationScreen({super.key});

  @override
  State<StudentVerificationScreen> createState() =>
      _StudentVerificationScreenState();
}

class _StudentVerificationScreenState extends State<StudentVerificationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _portalIdController = TextEditingController();
  final _portalPasswordController = TextEditingController();
  bool _isVerifying = false;

  @override
  void dispose() {
    _portalIdController.dispose();
    _portalPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('재학생 인증'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '연세대학교 재학생 인증',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              
              // Portal ID Input
              TextFormField(
                controller: _portalIdController,
                decoration: const InputDecoration(
                  labelText: '연세포탈 ID',
                  hintText: '학번 또는 포탈 ID',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '연세포탈 ID를 입력해주세요';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              
              // Portal Password Input
              TextFormField(
                controller: _portalPasswordController,
                decoration: const InputDecoration(
                  labelText: '연세포탈 비밀번호',
                  border: OutlineInputBorder(),
                ),
                obscureText: true,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '비밀번호를 입력해주세요';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              
              // Error Message
              const Text(
                '연세포탈 로그인이 확인되지 않았습니다.',
                style: TextStyle(
                  color: Colors.orange,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 24),
              
              // Verify Button
              ElevatedButton(
                onPressed: _isVerifying
                    ? null
                    : () async {
                        if (_formKey.currentState!.validate()) {
                          setState(() {
                            _isVerifying = true;
                          });
                          
                          // TODO: Verify student
                          await Future.delayed(const Duration(seconds: 2));
                          
                          if (mounted) {
                            setState(() {
                              _isVerifying = false;
                            });
                            
                            // Navigate to initial setup
                            context.push('/initial-setup');
                          }
                        }
                      },
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                ),
                child: _isVerifying
                    ? const CircularProgressIndicator()
                    : const Text('인증하기'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
