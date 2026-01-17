import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class InitialSetupScreen extends StatefulWidget {
  const InitialSetupScreen({super.key});

  @override
  State<InitialSetupScreen> createState() => _InitialSetupScreenState();
}

class _InitialSetupScreenState extends State<InitialSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firestore = FirebaseFirestore.instance;
  bool _isLoading = false;

  // Basic Info Controllers
  final _userNameController = TextEditingController();
  final _nicknameController = TextEditingController();
  final _introductionController = TextEditingController();
  final _mbtiController = TextEditingController();
  final _attachmentTypeController = TextEditingController();
  final _interestsController = TextEditingController();
  final _lifestyleController = TextEditingController();

  // Preferences Controllers
  final _preferredMbtiController = TextEditingController();
  final _preferredAttachmentTypeController = TextEditingController();
  final _preferredHeightController = TextEditingController();
  final _preferredAgeController = TextEditingController();
  final _preferredLifestyleController = TextEditingController();

  // Dropdown Values
  String? _gender;
  String? _department;
  String? _preferredGender;
  String? _preferredDepartment;

  @override
  void dispose() {
    _userNameController.dispose();
    _nicknameController.dispose();
    _introductionController.dispose();
    _mbtiController.dispose();
    _attachmentTypeController.dispose();
    _interestsController.dispose();
    _lifestyleController.dispose();
    _preferredMbtiController.dispose();
    _preferredAttachmentTypeController.dispose();
    _preferredHeightController.dispose();
    _preferredAgeController.dispose();
    _preferredLifestyleController.dispose();
    super.dispose();
  }

  Future<void> _saveToFirestore() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await _firestore.collection('users').add({
        // Basic Info
        'name': _userNameController.text.trim(),
        'nickname': _nicknameController.text.trim(),
        'gender': _gender,
        'introduction': _introductionController.text.trim(),
        'mbti': _mbtiController.text.trim(),
        'attachmentType': _attachmentTypeController.text.trim(),
        'department': _department,
        'interests': _interestsController.text.trim(),
        'lifestyle': _lifestyleController.text.trim(),
        
        // Preferences
        'preferredGender': _preferredGender,
        'preferredMbti': _preferredMbtiController.text.trim(),
        'preferredAttachmentType': _preferredAttachmentTypeController.text.trim(),
        'preferredDepartment': _preferredDepartment,
        'preferredHeight': _preferredHeightController.text.trim(),
        'preferredAge': _preferredAgeController.text.trim(),
        'preferredLifestyle': _preferredLifestyleController.text.trim(),
        
        // Metadata
        'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('프로필이 성공적으로 저장되었습니다!'),
            backgroundColor: Colors.green,
          ),
        );
        
        // Navigate to tutorial
        context.go('/tutorial');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('저장 실패: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('초기 설정'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '프로필을 설정해주세요',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              
              // Basic Info Section
              _buildSection(
                title: '기본 정보',
                children: [
                  _buildTextField('사용자 이름', _userNameController),
                  _buildTextField('닉네임', _nicknameController),
                  _buildDropdown('성별', ['남성', '여성'], (value) => _gender = value),
                  _buildTextField('자기소개 (선택)', _introductionController, isOptional: true),
                  _buildImagePicker('사진 등록'),
                  _buildTextField('MBTI', _mbtiController),
                  _buildTextField('애착유형', _attachmentTypeController),
                  _buildDropdown('학과계열', ['문과', '이과', '예체', '메디컬'], (value) => _department = value),
                  _buildTextField('관심사 (선택)', _interestsController, isOptional: true),
                  _buildTextField('생활 습관 (담배, 종교 등)', _lifestyleController),
                ],
              ),
              
              const SizedBox(height: 32),
              
              // Preferences Section
              _buildSection(
                title: '선호 취향',
                children: [
                  _buildDropdown('선호 성별', ['남성', '여성', '상관없음'], (value) => _preferredGender = value),
                  _buildTextField('선호 MBTI', _preferredMbtiController),
                  _buildTextField('선호 애착유형', _preferredAttachmentTypeController),
                  _buildDropdown('선호 학과계열', ['문과', '이과', '예체', '메디컬'], (value) => _preferredDepartment = value),
                  _buildTextField('선호 키', _preferredHeightController),
                  _buildTextField('선호 나이', _preferredAgeController),
                  _buildTextField('기타 생활 습관 비선호 항목', _preferredLifestyleController),
                ],
              ),
              
              const SizedBox(height: 32),
              
              // Complete Button
              ElevatedButton(
                onPressed: _isLoading ? null : _saveToFirestore,
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
                    : const Text('완료'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        ...children,
      ],
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, {bool isOptional = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: TextFormField(
        controller: controller,
        decoration: InputDecoration(
          labelText: label + (isOptional ? '' : ''),
          border: const OutlineInputBorder(),
        ),
        validator: isOptional
            ? null
            : (value) {
                if (value == null || value.trim().isEmpty) {
                  return '${label.replaceAll(' (선택)', '')}을(를) 입력해주세요';
                }
                return null;
              },
      ),
    );
  }

  Widget _buildDropdown(String label, List<String> items, Function(String?) onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: DropdownButtonFormField<String>(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        items: items.map((item) {
          return DropdownMenuItem(
            value: item,
            child: Text(item),
          );
        }).toList(),
        onChanged: onChanged,
        validator: (value) {
          if (value == null || value.isEmpty) {
            return '${label}을(를) 선택해주세요';
          }
          return null;
        },
      ),
    );
  }

  Widget _buildImagePicker(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () {
              // TODO: Implement image picker
            },
            icon: const Icon(Icons.add_photo_alternate),
            label: const Text('사진 추가'),
          ),
        ],
      ),
    );
  }
}
