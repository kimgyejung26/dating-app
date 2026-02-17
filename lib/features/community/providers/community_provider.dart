import 'package:flutter/cupertino.dart';

/// 커뮤니티 상태 관리 Provider
class CommunityProvider extends ChangeNotifier {
  bool _isLoading = false;
  List<dynamic> _posts = [];
  String _selectedCategory = '전체';

  bool get isLoading => _isLoading;
  List<dynamic> get posts => _posts;
  String get selectedCategory => _selectedCategory;

  /// 카테고리 변경
  void setCategory(String category) {
    _selectedCategory = category;
    loadPosts();
  }

  /// 게시글 로드
  Future<void> loadPosts() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _posts = []; // Mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 게시글 좋아요 토글
  Future<void> toggleLike(String postId) async {
    // TODO: 구현
  }
}
