import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:firebase_core/firebase_core.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'app.dart';
import 'firebase_options.dart';

void main() {
  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      // Kakao SDK init (App Key는 공개 키 성격)
      const kakaoNativeAppKey = 'cb08e2aea50a58b7d0c5e610e0c5a644';
      const kakaoJavaScriptKey = 'bff1db6356fcd7aaf5dc466080359ce0';

      KakaoSdk.init(
        nativeAppKey: kIsWeb ? null : kakaoNativeAppKey,
        javaScriptAppKey: kIsWeb ? kakaoJavaScriptKey : null,
      );

      // Firebase init (AuthService에서 FirebaseAuth.instance를 사용함)
      if (kIsWeb) {
        await Firebase.initializeApp(
          options: DefaultFirebaseOptions.currentPlatform,
        );
      } else {
        await Firebase.initializeApp();
      }

      runApp(const SeolleyeonApp());
    },
    (error, stack) {
      // 여기서는 로깅만 (앱 크래시 방지 목적)
      // ignore: avoid_print
      print('[GLOBAL] Uncaught error: $error\n$stack');
    },
  );
}
