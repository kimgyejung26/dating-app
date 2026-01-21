import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:provider/provider.dart';
import 'firebase_options.dart';
import 'providers/auth_provider.dart';
import 'routes/app_router.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // TODO: Replace these with your real Kakao keys.
  // 카카오 디벨로퍼스 설정 체크리스트:
  // - Android 플랫폼 등록(패키지명 + 키 해시)
  // - iOS 플랫폼 등록(Bundle ID + URL Scheme)
  // - Web 플랫폼 등록(도메인 + JavaScript 키)
  const String kakaoNativeAppKey = 'cb08e2aea50a58b7d0c5e610e0c5a644';
  const String kakaoJavaScriptKey = 'bff1db6356fcd7aaf5dc466080359ce0';

  KakaoSdk.init(
    // 가능한 한 플랫폼 분기를 최소화하되, Web/Native 키를 모두 지정
    nativeAppKey: kIsWeb ? null : kakaoNativeAppKey,
    javaScriptAppKey: kIsWeb ? kakaoJavaScriptKey : null,
  );

  // Firebase 초기화
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
      ],
      child: Builder(
        builder: (context) {
          final authProvider = context.watch<AuthProvider>();
          return MaterialApp.router(
            title: '설레연',
            debugShowCheckedModeBanner: false,
            theme: ThemeData(
              colorScheme: ColorScheme.fromSeed(
                seedColor: Colors.pink,
                brightness: Brightness.light,
              ),
              useMaterial3: true,
            ),
            routerConfig: AppRouter.router(authProvider),
          );
        },
      ),
    );
  }
}
