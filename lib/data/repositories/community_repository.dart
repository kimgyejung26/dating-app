import '../models/community/post_model.dart';

/// 커뮤니티 리포지토리
abstract class CommunityRepository {
  /// 게시글 목록 조회
  Future<List<PostModel>> getPosts({
    String? category,
    int page = 1,
    int limit = 20,
  });

  /// 게시글 상세 조회
  Future<PostModel> getPost(String postId);

  /// 게시글 작성
  Future<PostModel> createPost({
    required String category,
    required String title,
    required String content,
    List<String>? imagePaths,
  });

  /// 게시글 수정
  Future<PostModel> updatePost(String postId, {String? title, String? content});

  /// 게시글 삭제
  Future<void> deletePost(String postId);

  /// 게시글 좋아요/취소
  Future<bool> toggleLike(String postId);

  /// 댓글 목록 조회
  Future<List<CommentModel>> getComments(String postId);

  /// 댓글 작성
  Future<CommentModel> createComment(String postId, String content);

  /// 댓글 삭제
  Future<void> deleteComment(String commentId);
}
