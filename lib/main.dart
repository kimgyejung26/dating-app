import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:firebase_core/firebase_core.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'firebase_options.dart';
import 'app.dart';

void main() {
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    // ✅ Kakao init (반드시 runApp 전에)
    const kakaoNativeAppKey = 'cb08e2aea50a58b7d0c5e610e0c5a644';
    const kakaoJavaScriptKey = 'bff1db6356fcd7aaf5dc466080359ce0';
    KakaoSdk.init(
      nativeAppKey: kIsWeb ? null : kakaoNativeAppKey,
      javaScriptAppKey: kIsWeb ? kakaoJavaScriptKey : null,
    );

    // ✅ Firebase init (모든 플랫폼에서 options로 통일하면 꼬일 확률이 줄어듦)
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );

    runApp(const SeolleyeonApp());
  }, (error, stack) {
    // ✅ iOS에서 조용히 죽는 것 방지용: 최소 로그라도 남김
    // ignore: avoid_print
    print('[GLOBAL] Uncaught error: $error\n$stack');
  });
}