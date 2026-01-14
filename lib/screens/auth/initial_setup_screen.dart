import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class InitialSetupScreen extends StatelessWidget {
  const InitialSetupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('초기 설정'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
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
                _buildTextField('사용자 이름'),
                _buildTextField('닉네임'),
                _buildDropdown('성별', ['남성', '여성']),
                _buildTextField('자기소개 (선택)', isOptional: true),
                _buildImagePicker('사진 등록'),
                _buildTextField('MBTI'),
                _buildTextField('애착유형'),
                _buildDropdown('학과계열', ['문과', '이과', '예체', '메디컬']),
                _buildTextField('관심사 (선택)', isOptional: true),
                _buildTextField('생활 습관 (담배, 종교 등)'),
              ],
            ),
            
            const SizedBox(height: 32),
            
            // Preferences Section
            _buildSection(
              title: '선호 취향',
              children: [
                _buildDropdown('선호 성별', ['남성', '여성', '상관없음']),
                _buildTextField('선호 MBTI'),
                _buildTextField('선호 애착유형'),
                _buildDropdown('선호 학과계열', ['문과', '이과', '예체', '메디컬']),
                _buildTextField('선호 키'),
                _buildTextField('선호 나이'),
                _buildTextField('기타 생활 습관 비선호 항목'),
              ],
            ),
            
            const SizedBox(height: 32),
            
            // Complete Button
            ElevatedButton(
              onPressed: () {
                // TODO: Save initial setup
                // Navigate to tutorial or main
                context.go('/tutorial');
              },
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 50),
              ),
              child: const Text('완료'),
            ),
          ],
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

  Widget _buildTextField(String label, {bool isOptional = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: TextField(
        decoration: InputDecoration(
          labelText: label + (isOptional ? ' (선택)' : ''),
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }

  Widget _buildDropdown(String label, List<String> items) {
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
        onChanged: (value) {},
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
