/// 설레연 앱 에셋 경로 상수
class AssetPaths {
  AssetPaths._();

  // Base paths
  static const String _images = 'assets/images';
  static const String _icons = 'assets/icons';
  static const String _animations = 'assets/animations';

  // Logo & Branding
  static const String logo = '$_images/logo.png';
  static const String logoWhite = '$_images/logo_white.png';
  static const String splash = '$_images/splash.png';

  // Icons
  static const String iconHeart = '$_icons/heart.svg';
  static const String iconHeartFilled = '$_icons/heart_filled.svg';
  static const String iconChat = '$_icons/chat.svg';
  static const String iconProfile = '$_icons/profile.svg';
  static const String iconSettings = '$_icons/settings.svg';

  // Navigation Icons
  static const String navMatching = '$_icons/nav_matching.svg';
  static const String navCommunity = '$_icons/nav_community.svg';
  static const String navEvent = '$_icons/nav_event.svg';
  static const String navChat = '$_icons/nav_chat.svg';
  static const String navProfile = '$_icons/nav_profile.svg';

  // Animations
  static const String animationMatch = '$_animations/match.json';
  static const String animationSlot = '$_animations/slot_machine.json';

  // Placeholders
  static const String placeholderProfile = '$_images/placeholder_profile.png';
  static const String placeholderImage = '$_images/placeholder_image.png';
}
