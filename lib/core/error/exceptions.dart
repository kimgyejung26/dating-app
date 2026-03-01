// 앱 예외 클래스 정의

/// 기본 앱 예외
class AppException implements Exception {
  final String message;
  final String? code;

  AppException(this.message, {this.code});

  @override
  String toString() => message;
}

/// API 관련 예외
class ApiException extends AppException {
  ApiException(super.message, {super.code});
}

/// 네트워크 예외
class NetworkException extends AppException {
  NetworkException(super.message) : super(code: 'NETWORK_ERROR');
}

/// 인증 필요 예외 (401)
class UnauthorizedException extends AppException {
  UnauthorizedException(super.message) : super(code: 'UNAUTHORIZED');
}

/// 접근 금지 예외 (403)
class ForbiddenException extends AppException {
  ForbiddenException(super.message) : super(code: 'FORBIDDEN');
}

/// 리소스 없음 예외 (404)
class NotFoundException extends AppException {
  NotFoundException(super.message) : super(code: 'NOT_FOUND');
}

/// 서버 에러 예외 (5xx)
class ServerException extends AppException {
  ServerException(super.message) : super(code: 'SERVER_ERROR');
}

/// 유효성 검사 예외
class ValidationException extends AppException {
  final Map<String, String>? fieldErrors;

  ValidationException(super.message, {this.fieldErrors})
    : super(code: 'VALIDATION_ERROR');
}

/// 캐시 예외
class CacheException extends AppException {
  CacheException(super.message) : super(code: 'CACHE_ERROR');
}
