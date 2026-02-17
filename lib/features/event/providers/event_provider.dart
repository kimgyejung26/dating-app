import 'package:flutter/cupertino.dart';

/// 이벤트(3:3 매칭) 상태 관리 Provider
class EventProvider extends ChangeNotifier {
  bool _isLoading = false;
  String _matchStatus = 'idle'; // idle, waiting, matching, matched

  bool get isLoading => _isLoading;
  String get matchStatus => _matchStatus;

  /// 3:3 매칭 시작
  Future<void> startGroupMatch() async {
    _isLoading = true;
    _matchStatus = 'waiting';
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 2));
      _matchStatus = 'matching';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 매칭 취소
  Future<void> cancelMatch() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(milliseconds: 500));
      _matchStatus = 'idle';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
