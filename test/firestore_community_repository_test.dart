import 'package:flutter_test/flutter_test.dart';
import 'package:seolleyeon/data/repositories/firestore_community_repository.dart';

void main() {
  group('FirestoreCommunityRepository collection partition', () {
    test('reviewer reads and writes only the review Bamboo roots', () {
      expect(
        FirestoreCommunityRepository.postsCollectionForUserId(
          'play-reviewer-v1',
        ),
        'playReviewBambooPosts',
      );
      expect(
        FirestoreCommunityRepository.postAuthorsCollectionForUserId(
          'play-reviewer-v1',
        ),
        'playReviewBambooPostAuthors',
      );
      expect(
        FirestoreCommunityRepository.commentAuthorsCollectionForUserId(
          'play-reviewer-v1',
        ),
        'playReviewBambooCommentAuthors',
      );
    });

    test('ordinary users retain the production Bamboo roots', () {
      expect(
        FirestoreCommunityRepository.postsCollectionForUserId('member-1'),
        'bamboo_posts',
      );
      expect(
        FirestoreCommunityRepository.postAuthorsCollectionForUserId(null),
        'bamboo_post_authors',
      );
      expect(
        FirestoreCommunityRepository.commentAuthorsCollectionForUserId(
          'member-1',
        ),
        'bamboo_comment_authors',
      );
    });
  });
}
