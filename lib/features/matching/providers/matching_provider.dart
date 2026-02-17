import 'package:flutter/cupertino.dart';

/// 매칭 상태 관리 Provider
class MatchingProvider extends ChangeNotifier {
  bool _isLoading = false;
  List<dynamic> _matchCards = [];
  int _currentCardIndex = 0;

  bool get isLoading => _isLoading;
  List<dynamic> get matchCards => _matchCards;
  dynamic get currentCard => _currentCardIndex < _matchCards.length
      ? _matchCards[_currentCardIndex]
      : null;

  /// 매칭 카드 로드
  Future<void> loadMatchCards() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _matchCards = []; // Mock data
      _currentCardIndex = 0;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 좋아요
  Future<bool> like() async {
    if (currentCard == null) return false;

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(milliseconds: 300));
      _moveToNextCard();
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 패스
  Future<void> pass() async {
    if (currentCard == null) return;

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(milliseconds: 300));
      _moveToNextCard();
    } catch (e) {
      // Handle error
    }
  }

  void _moveToNextCard() {
    _currentCardIndex++;
    notifyListeners();

    // 카드가 부족하면 더 로드
    if (_currentCardIndex >= _matchCards.length - 2) {
      loadMatchCards();
    }
  }
}
