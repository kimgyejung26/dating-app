/// API 엔드포인트 상수
class ApiEndpoints {
  ApiEndpoints._();

  /// 기본 URL
  static const String baseUrl = 'https://api.seolleyeon.com/v1';

  // Auth
  static const String authKakao = '/auth/kakao';
  static const String authRefresh = '/auth/refresh';
  static const String authLogout = '/auth/logout';

  // User
  static const String userProfile = '/users/me';
  static const String userUpdate = '/users/me';
  static const String userPhotos = '/users/me/photos';

  // Matching
  static const String matchingCards = '/matching/cards';
  static const String matchingLike = '/matching/like';
  static const String matchingPass = '/matching/pass';
  static const String matchingPreferences = '/matching/preferences';

  // Community
  static const String communityPosts = '/community/posts';
  static const String communityComments = '/community/comments';

  // Event
  static const String eventGroupMatch = '/events/3v3';
  static const String eventSlotMachine = '/events/slot-machine';

  // Chat
  static const String chatRooms = '/chat/rooms';
  static const String chatMessages = '/chat/messages';

  // Hearts
  static const String heartsBalance = '/hearts/balance';
  static const String heartsPurchase = '/hearts/purchase';
}
