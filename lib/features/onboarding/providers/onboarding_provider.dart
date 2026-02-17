import 'package:flutter/cupertino.dart';

/// 온보딩 상태 관리 Provider
class OnboardingProvider extends ChangeNotifier {
  int _currentStep = 1;
  final int _totalSteps = 6;
  bool _isLoading = false;

  // 기본 정보
  String? _nickname;
  int? _height;
  String? _bodyType;
  String? _department;

  // 관심사/키워드
  List<String> _interests = [];
  List<String> _keywords = [];

  // 사진
  List<String> _photoUrls = [];

  // 자기소개
  String? _introduction;

  // 이상형
  int? _idealMinAge;
  int? _idealMaxAge;
  int? _idealMinHeight;
  int? _idealMaxHeight;
  List<String> _idealMbti = [];
  List<String> _idealDepartments = [];

  // Getters
  int get currentStep => _currentStep;
  int get totalSteps => _totalSteps;
  bool get isLoading => _isLoading;
  double get progress => _currentStep / _totalSteps;

  String? get nickname => _nickname;
  int? get height => _height;
  List<String> get interests => _interests;
  List<String> get keywords => _keywords;
  List<String> get photoUrls => _photoUrls;
  String? get introduction => _introduction;

  /// 다음 스텝으로 이동
  void nextStep() {
    if (_currentStep < _totalSteps) {
      _currentStep++;
      notifyListeners();
    }
  }

  /// 이전 스텝으로 이동
  void previousStep() {
    if (_currentStep > 1) {
      _currentStep--;
      notifyListeners();
    }
  }

  /// 기본 정보 설정
  void setBasicInfo({
    String? nickname,
    int? height,
    String? bodyType,
    String? department,
  }) {
    _nickname = nickname ?? _nickname;
    _height = height ?? _height;
    _bodyType = bodyType ?? _bodyType;
    _department = department ?? _department;
    notifyListeners();
  }

  /// 관심사 설정
  void setInterests(List<String> interests) {
    _interests = interests;
    notifyListeners();
  }

  /// 키워드 설정
  void setKeywords(List<String> keywords) {
    _keywords = keywords;
    notifyListeners();
  }

  /// 사진 추가
  void addPhoto(String url) {
    if (_photoUrls.length < 6) {
      _photoUrls.add(url);
      notifyListeners();
    }
  }

  /// 사진 삭제
  void removePhoto(int index) {
    if (index < _photoUrls.length) {
      _photoUrls.removeAt(index);
      notifyListeners();
    }
  }

  /// 자기소개 설정
  void setIntroduction(String introduction) {
    _introduction = introduction;
    notifyListeners();
  }

  /// 이상형 설정
  void setIdealType({
    int? minAge,
    int? maxAge,
    int? minHeight,
    int? maxHeight,
    List<String>? mbti,
    List<String>? departments,
  }) {
    _idealMinAge = minAge ?? _idealMinAge;
    _idealMaxAge = maxAge ?? _idealMaxAge;
    _idealMinHeight = minHeight ?? _idealMinHeight;
    _idealMaxHeight = maxHeight ?? _idealMaxHeight;
    _idealMbti = mbti ?? _idealMbti;
    _idealDepartments = departments ?? _idealDepartments;
    notifyListeners();
  }

  /// 온보딩 완료
  Future<bool> completeOnboarding() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: API 호출
      await Future.delayed(const Duration(seconds: 1));
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// 초기화
  void reset() {
    _currentStep = 1;
    _nickname = null;
    _height = null;
    _bodyType = null;
    _department = null;
    _interests = [];
    _keywords = [];
    _photoUrls = [];
    _introduction = null;
    notifyListeners();
  }
}
