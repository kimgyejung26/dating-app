/// 커뮤니티 게시글 모델
class PostModel {
  final String id;
  final String authorId;
  final String authorNickname;
  final String? authorProfileUrl;
  final String category;
  final String title;
  final String content;
  final List<String> imageUrls;
  final int likeCount;
  final int commentCount;
  final int viewCount;
  final bool isLiked;
  final DateTime createdAt;
  final DateTime updatedAt;

  const PostModel({
    required this.id,
    required this.authorId,
    required this.authorNickname,
    this.authorProfileUrl,
    required this.category,
    required this.title,
    required this.content,
    this.imageUrls = const [],
    this.likeCount = 0,
    this.commentCount = 0,
    this.viewCount = 0,
    this.isLiked = false,
    required this.createdAt,
    required this.updatedAt,
  });

  factory PostModel.fromJson(Map<String, dynamic> json) {
    return PostModel(
      id: json['id'] as String,
      authorId: json['authorId'] as String,
      authorNickname: json['authorNickname'] as String,
      authorProfileUrl: json['authorProfileUrl'] as String?,
      category: json['category'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      imageUrls:
          (json['imageUrls'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      likeCount: json['likeCount'] as int? ?? 0,
      commentCount: json['commentCount'] as int? ?? 0,
      viewCount: json['viewCount'] as int? ?? 0,
      isLiked: json['isLiked'] as bool? ?? false,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'authorId': authorId,
      'authorNickname': authorNickname,
      'authorProfileUrl': authorProfileUrl,
      'category': category,
      'title': title,
      'content': content,
      'imageUrls': imageUrls,
      'likeCount': likeCount,
      'commentCount': commentCount,
      'viewCount': viewCount,
      'isLiked': isLiked,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
    };
  }
}

/// 댓글 모델
class CommentModel {
  final String id;
  final String postId;
  final String authorId;
  final String authorNickname;
  final String? authorProfileUrl;
  final String content;
  final int likeCount;
  final bool isLiked;
  final DateTime createdAt;

  const CommentModel({
    required this.id,
    required this.postId,
    required this.authorId,
    required this.authorNickname,
    this.authorProfileUrl,
    required this.content,
    this.likeCount = 0,
    this.isLiked = false,
    required this.createdAt,
  });

  factory CommentModel.fromJson(Map<String, dynamic> json) {
    return CommentModel(
      id: json['id'] as String,
      postId: json['postId'] as String,
      authorId: json['authorId'] as String,
      authorNickname: json['authorNickname'] as String,
      authorProfileUrl: json['authorProfileUrl'] as String?,
      content: json['content'] as String,
      likeCount: json['likeCount'] as int? ?? 0,
      isLiked: json['isLiked'] as bool? ?? false,
      createdAt: DateTime.parse(json['createdAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'postId': postId,
      'authorId': authorId,
      'authorNickname': authorNickname,
      'authorProfileUrl': authorProfileUrl,
      'content': content,
      'likeCount': likeCount,
      'isLiked': isLiked,
      'createdAt': createdAt.toIso8601String(),
    };
  }
}
