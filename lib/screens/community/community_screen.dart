import 'package:flutter/material.dart';
import '../../design_system/design_system.dart';
import '../../mock/mock_posts.dart';

class CommunityScreen extends StatefulWidget {
  const CommunityScreen({super.key});

  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  int _selectedTabIndex = 0;

  List<MockPost> get _filteredPosts {
    if (_selectedTabIndex == 0) return MockPosts.posts;
    // Filter by popularity (likes > 50) for index 1
    if (_selectedTabIndex == 1) {
      return MockPosts.posts.where((p) => p.likeCount > 50).toList();
    }
    // Filter for excitement tags for index 2
    return MockPosts.posts
        .where((p) => p.tag == '두근' || p.tag == '썸사랑' || p.tag == '첫만남')
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return SeolScaffold(
      appBar: SeolMainAppBar(
        title: '대나무숲',
        onNotificationTap: () {
          // TODO: Navigate to notifications
        },
      ),
      body: Column(
        children: [
          // Filter Tabs
          SeolFilterTabs(
            tabs: MockPosts.filterTabs,
            selectedIndex: _selectedTabIndex,
            onTabSelected: (i) => setState(() => _selectedTabIndex = i),
          ),
          const SizedBox(height: 12),
          // Posts List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              itemCount: _filteredPosts.length,
              itemBuilder: (context, index) {
                final post = _filteredPosts[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: SeolPostCard(
                    tag: post.tag,
                    timeAgo: post.timeAgo,
                    content: post.content,
                    likeCount: post.likeCount,
                    commentCount: post.commentCount,
                    onTap: () {
                      // TODO: Navigate to post detail
                    },
                    onLike: () {
                      // TODO: Toggle like
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Navigate to create post
        },
        backgroundColor: SeolColors.primary,
        child: const Icon(Icons.edit, color: SeolColors.textWhite),
      ),
    );
  }
}
