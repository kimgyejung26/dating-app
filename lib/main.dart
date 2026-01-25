import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:firebase_core/firebase_core.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:provider/provider.dart';

import 'firebase_options.dart';
import 'providers/auth_provider.dart';
import 'routes/app_router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  const String kakaoNativeAppKey = 'cb08e2aea50a58b7d0c5e610e0c5a644';
  const String kakaoJavaScriptKey = 'bff1db6356fcd7aaf5dc466080359ce0';

  KakaoSdk.init(
    nativeAppKey: kIsWeb ? null : kakaoNativeAppKey,
    javaScriptAppKey: kIsWeb ? kakaoJavaScriptKey : null,
  );

  // ✅ Firebase 초기화가 진짜 되는지 로그로 확인
  await runZonedGuarded(
    () async {
      try {
        if (kIsWeb) {
          debugPrint('[Firebase] init WEB with options');
          await Firebase.initializeApp(
            options: DefaultFirebaseOptions.currentPlatform,
          );
        } else {
          // ✅ iOS/Android는 각 플랫폼 설정(ios는 GoogleService-Info.plist)을 우선 사용
          debugPrint('[Firebase] init NATIVE default (plist/google-services)');
          await Firebase.initializeApp();
        }
        debugPrint(
          '[Firebase] init DONE: ${Firebase.apps.map((e) => e.name).toList()}',
        );
      } catch (e, st) {
        debugPrint('[Firebase] init FAILED: $e\n$st');
        rethrow;
      }

      runApp(const DatingApp());
    },
    (error, stack) {
      debugPrint('[ZONED] Uncaught error: $error\n$stack');
    },
  );
}

class DatingApp extends StatelessWidget {
  const DatingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: Builder(
        builder: (context) {
          final authProvider = context.read<AuthProvider>();
          return MaterialApp.router(
            debugShowCheckedModeBanner: false,
            routerConfig: AppRouter.router(authProvider),
            title: 'Dating App',
          );
        },
      ),
    );
  }
}
