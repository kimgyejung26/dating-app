import 'package:flutter/widgets.dart';

/// 현재 최상위 "이름 있는" 라우트를 추적하는 NavigatorObserver.
///
/// 다이얼로그/바텀시트처럼 이름이 없는 라우트는 건너뛰므로, 온보딩 화면 위에
/// 다이얼로그가 떠 있어도 [currentRouteName] 은 그 화면 이름을 유지한다.
/// `MaterialApp.builder` 위에서 화면 전환에 독립적으로 "지금 온보딩 구간인가"를
/// 판단해야 하는 앱 레벨 오버레이가 이 값을 구독한다.
class CurrentRouteObserver extends NavigatorObserver {
  final List<Route<dynamic>> _stack = <Route<dynamic>>[];

  final ValueNotifier<String?> currentRouteName = ValueNotifier<String?>(null);

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _stack.add(route);
    _publish();
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _stack.remove(route);
    _publish();
  }

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _stack.remove(route);
    _publish();
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    final index = oldRoute == null ? -1 : _stack.indexOf(oldRoute);
    if (index >= 0) {
      if (newRoute != null) {
        _stack[index] = newRoute;
      } else {
        _stack.removeAt(index);
      }
    } else if (newRoute != null) {
      _stack.add(newRoute);
    }
    _publish();
  }

  void _publish() {
    String? name;
    for (var i = _stack.length - 1; i >= 0; i--) {
      final candidate = _stack[i].settings.name;
      if (candidate != null && candidate.isNotEmpty) {
        name = candidate;
        break;
      }
    }
    if (currentRouteName.value != name) {
      currentRouteName.value = name;
    }
  }
}
