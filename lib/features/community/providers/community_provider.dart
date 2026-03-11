import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';

import '../../../data/models/community/post_model.dart';
import '../../../data/repositories/firestore_community_repository.dart';

class CommunityProvider extends ChangeNotifier {
  CommunityProvider({FirestoreCommunityRepository? repository})
    : _repository = repository ?? FirestoreCommunityRepository();

  final FirestoreCommunityRepository _repository;

  static const List<String> tabs = ['전체', '인기', '설렘', '고민', '일상', '질문'];

  final Map<String, List<PostModel>> _postsByTab = {
    for (final tab in tabs) tab: <PostModel>[],
  };

  final Map<String, DocumentSnapshot<Map<String, dynamic>>?> _lastDocByTab = {
    for (final tab in tabs) tab: null,
  };

  final Map<String, bool> _isLoadingByTab = {
    for (final tab in tabs) tab: false,
  };

  final Map<String, bool> _isLoadingMoreByTab = {
    for (final tab in tabs) tab: false,
  };

  final Map<String, bool> _hasMoreByTab = {for (final tab in tabs) tab: true};

  String _selectedTab = '전체';
  bool _isInitialized = false;

  String get selectedTab => _selectedTab;
  bool get isInitialized => _isInitialized;

  List<PostModel> get posts => _postsByTab[_selectedTab] ?? const [];
  bool get isLoading => _isLoadingByTab[_selectedTab] ?? false;
  bool get isLoadingMore => _isLoadingMoreByTab[_selectedTab] ?? false;
  bool get hasMore => _hasMoreByTab[_selectedTab] ?? false;

  List<PostModel> postsOf(String tab) => _postsByTab[tab] ?? const [];
  bool isLoadingOf(String tab) => _isLoadingByTab[tab] ?? false;
  bool isLoadingMoreOf(String tab) => _isLoadingMoreByTab[tab] ?? false;
  bool hasMoreOf(String tab) => _hasMoreByTab[tab] ?? false;

  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;
    await loadPosts(tab: _selectedTab, forceRefresh: true);
  }

  Future<void> changeTab(String tab) async {
    if (!tabs.contains(tab)) return;

    _selectedTab = tab;
    notifyListeners();

    final hasLoaded = (_postsByTab[tab] ?? []).isNotEmpty;
    if (!hasLoaded) {
      await loadPosts(tab: tab, forceRefresh: true);
    }
  }

  Future<void> loadPosts({
    required String tab,
    bool forceRefresh = false,
  }) async {
    if (!tabs.contains(tab)) return;
    if ((_isLoadingByTab[tab] ?? false) && !forceRefresh) return;

    _isLoadingByTab[tab] = true;

    if (forceRefresh) {
      _postsByTab[tab] = [];
      _lastDocByTab[tab] = null;
      _hasMoreByTab[tab] = true;
    }

    notifyListeners();

    try {
      final snapshot = await _repository.fetchPostsSnapshot(
        tab: tab,
        limit: 5,
        lastDocument: null,
      );

      final docs = snapshot.docs;
      final loadedPosts = docs.map(PostModel.fromFirestore).toList();

      _postsByTab[tab] = loadedPosts;
      _lastDocByTab[tab] = docs.isNotEmpty ? docs.last : null;
      _hasMoreByTab[tab] = docs.length == 5;
    } catch (e, st) {
      debugPrint('CommunityProvider loadPosts error: $e');
      debugPrintStack(stackTrace: st);
    } finally {
      _isLoadingByTab[tab] = false;
      notifyListeners();
    }
  }

  Future<void> loadMore({String? tab}) async {
    final targetTab = tab ?? _selectedTab;
    if (!tabs.contains(targetTab)) return;

    if (_isLoadingMoreByTab[targetTab] == true) return;
    if (_hasMoreByTab[targetTab] != true) return;

    final lastDoc = _lastDocByTab[targetTab];
    if (lastDoc == null) return;

    _isLoadingMoreByTab[targetTab] = true;
    notifyListeners();

    try {
      final snapshot = await _repository.fetchPostsSnapshot(
        tab: targetTab,
        limit: 5,
        lastDocument: lastDoc,
      );

      final docs = snapshot.docs;
      final newPosts = docs.map(PostModel.fromFirestore).toList();

      final currentPosts = [...(_postsByTab[targetTab] ?? <PostModel>[])];
      currentPosts.addAll(newPosts);

      _postsByTab[targetTab] = currentPosts;
      _lastDocByTab[targetTab] = docs.isNotEmpty ? docs.last : lastDoc;
      _hasMoreByTab[targetTab] = docs.length == 5;
    } catch (e, st) {
      debugPrint('CommunityProvider loadMore error: $e');
      debugPrintStack(stackTrace: st);
    } finally {
      _isLoadingMoreByTab[targetTab] = false;
      notifyListeners();
    }
  }

  Future<String?> createPost({
    required String authorId,
    required String content,
    required String category,
    required List<String> tags,
  }) async {
    try {
      final postId = await _repository.createPost(
        authorId: authorId,
        content: content,
        category: category,
        tags: tags,
      );

      // 글 작성 후 전체 / 해당 카테고리 / 인기 탭은 새로고침
      await refreshAfterPostCreated(category: category);
      return postId;
    } catch (e, st) {
      debugPrint('CommunityProvider createPost error: $e');
      debugPrintStack(stackTrace: st);
      return null;
    }
  }

  Future<void> refreshAfterPostCreated({required String category}) async {
    await loadPosts(tab: '전체', forceRefresh: true);

    if (tabs.contains(category)) {
      await loadPosts(tab: category, forceRefresh: true);
    }

    await loadPosts(tab: '인기', forceRefresh: true);
  }

  Future<void> refreshCurrentTab() async {
    await loadPosts(tab: _selectedTab, forceRefresh: true);
  }

  Future<void> togglePostLike({
    required String postId,
    required String userId,
  }) async {
    try {
      await _repository.togglePostLike(postId: postId, userId: userId);

      // 좋아요 수 즉시 반영하려면 현재 탭만 새로고침
      await refreshCurrentTab();
    } catch (e, st) {
      debugPrint('CommunityProvider togglePostLike error: $e');
      debugPrintStack(stackTrace: st);
    }
  }

  Future<PostModel?> fetchPostDetail(String postId) async {
    try {
      return await _repository.fetchPostDetail(postId);
    } catch (e, st) {
      debugPrint('CommunityProvider fetchPostDetail error: $e');
      debugPrintStack(stackTrace: st);
      return null;
    }
  }

  Future<void> deletePost({
    required String postId,
    required String authorId,
  }) async {
    try {
      await _repository.softDeletePost(postId: postId, authorId: authorId);

      // 삭제 후 모든 탭 중 현재 로드된 탭만 새로고침
      for (final tab in tabs) {
        if ((_postsByTab[tab] ?? []).isNotEmpty || tab == _selectedTab) {
          await loadPosts(tab: tab, forceRefresh: true);
        }
      }
    } catch (e, st) {
      debugPrint('CommunityProvider deletePost error: $e');
      debugPrintStack(stackTrace: st);
    }
  }

  PostModel? findPostById(String postId) {
    for (final tab in tabs) {
      final post = (_postsByTab[tab] ?? []).cast<PostModel?>().firstWhere(
        (p) => p?.postId == postId,
        orElse: () => null,
      );
      if (post != null) return post;
    }
    return null;
  }
}
