# Seolleyeon AI Profile Prompt v3

이 패키지는 설레연의 **AI에게 내 취향 알려주기** 기능에 들어가는 AI 프로필 이미지를 만들기 위한 metadata-first prompt builder입니다.

설레연 기준:

- 가벼운 만남 앱 톤이 아니라, 대학생 전용 신뢰형 관계 플랫폼 톤을 유지합니다.
- AI 프로필은 실제 사용자를 대체하지 않고, 추천 시스템의 cold start와 취향 벡터 초기화를 위한 synthetic profile asset입니다.
- 얼굴 / 체형 / 스타일 / 구도 / 배경을 분리해서 제어합니다.
- `face_card`, `silhouette_card`, `vibe_card` 3개 샷 패밀리를 지원합니다.
- 현재 CLIP 경로 호환을 위해 `ai_profiles/female/137.png` 같은 legacy path도 함께 기록합니다.

---

## 파일 구성

```text
seolleyeon_ai_profile_prompt_v3.py      # 메인 prompt/spec builder
ai_profile_prompt_v3_seed_batch_024/    # 24명 × 3샷 샘플 배치
ai_profile_prompt_v3_mvp_batch_240/     # 240명 × 3샷 MVP 배치
seolleyeon_clip_train_export_ai_v3.patch # 선택 적용용 CLIP multi-shot 경로 패치
```

---

## 1. 단일 spec 생성

```bash
python seolleyeon_ai_profile_prompt_v3.py sample \
  --gender female \
  --numeric_id 137
```

asset prompt까지 같이 보고 싶으면:

```bash
python seolleyeon_ai_profile_prompt_v3.py sample \
  --gender female \
  --numeric_id 137 \
  --as_assets
```

---

## 2. 배치 생성

24명 테스트 배치:

```bash
python seolleyeon_ai_profile_prompt_v3.py batch \
  --female_count 12 \
  --male_count 12 \
  --out_dir ./ai_profile_prompt_v3_seed_batch_024
```

MVP 240명 배치:

```bash
python seolleyeon_ai_profile_prompt_v3.py batch \
  --female_count 120 \
  --male_count 120 \
  --out_dir ./ai_profile_prompt_v3_mvp_batch_240
```

출력 파일:

```text
ai_profile_specs_v3.jsonl   # identity-level metadata
ai_profile_assets_v3.jsonl  # shot-level prompt records
ai_profile_assets_v3.csv    # 생성툴 투입용 CSV
```

---

## 3. 생성 경로 구조

기존 CLIP 호환 대표 이미지:

```text
ai_profiles/female/137.png
ai_profiles/male/084.png
```

v3 multi-shot 이미지:

```text
ai_profiles/female/137/face_card.png
ai_profiles/female/137/silhouette_card.png
ai_profiles/female/137/vibe_card.png
```

권장 운영:

```text
1. face_card를 canonical portrait로 생성
2. 같은 인물 유지 방식으로 silhouette_card / vibe_card 파생
3. QA 통과 이미지 업로드
4. face_card 또는 가장 안정적인 이미지를 legacy 대표 이미지로도 복사
5. recEvents.targetId는 female_137 / male_084 형태로 저장
```

---

## 4. recEvents 예시

```json
{
  "userId": "user_abc",
  "type": "like",
  "targetId": "female_137",
  "targetType": "ai_profile",
  "createdAt": "2026-05-04T00:00:00.000Z",
  "context": {
    "surface": "ai_preference_onboarding",
    "targetType": "ai_profile",
    "assetId": "female_137__face_card__v001",
    "shotType": "face_card",
    "metadataVersion": "ai_profile_image_v3",
    "storagePath": "ai_profiles/female/137/face_card.png",
    "legacyStoragePath": "ai_profiles/female/137.png"
  }
}
```

버튼 카피는 내부 이벤트명과 분리하는 것을 권장합니다.

```text
like → 느낌이 좋아요
nope → 아닌 것 같아요
```

---

## 5. CLIP multi-shot 옵션

현재 추천 코드가 legacy 대표 이미지 1장을 읽는 구조라면 그대로 사용하면 됩니다.

v3 multi-shot 평균 임베딩을 쓰고 싶을 때만 `seolleyeon_clip_train_export_ai_v3.patch`를 적용하고, 이미지 3장이 모두 업로드된 뒤 다음 환경변수를 켭니다.

```bash
export AI_PROFILE_ASSET_LAYOUT=v3_multishot
```

지원 layout:

```text
legacy       # 기본값. ai_profiles/female/137.png 1장
v3_multishot # face_card/silhouette_card/vibe_card 3장
v3_hybrid    # legacy + v3 path. 실험용
```

주의: `v3_multishot`은 3개 이미지가 모두 업로드된 뒤 켜야 합니다. 일부 파일이 없으면 해당 AI profile embedding이 실패할 수 있습니다.

---

## 6. QA 체크리스트

생성 이미지는 최소 아래 항목을 통과해야 합니다.

```text
- 성인 대학생처럼 보이는가?
- 미성년/교복/아이돌 연습생 느낌이 없는가?
- 과도한 화보, 광고, 인플루언서 촬영처럼 보이지 않는가?
- 노출/성적 포즈/클럽/네온/파티 느낌이 없는가?
- 실제 대학생이 올릴 법한 자연스러운 프로필인가?
- face_card는 얼굴상과 인상이 읽히는가?
- silhouette_card는 체형/프레임/비율이 읽히는가?
- vibe_card는 패션/라이프스타일/무드가 읽히는가?
- 배경에 학교명, 로고, 읽을 수 있는 텍스트가 없는가?
- metadata와 실제 이미지가 일치하는가?
- 같은 identity의 3장이 같은 사람처럼 보이는가?
```

---

## 7. 추천 운영 메모

MVP 권장:

```text
CLIP: AI profile like/nope 적극 반영
KNN: AI profile like/nope 반영
SVD: 초기에는 제외 또는 별도 옵션 실험
RRF: CLIP 우선, KNN 보조, 실제 유저 신호가 쌓이면 SVD/KNN 비중 증가
```

AI 프로필 반응은 실제 관계 신호가 쌓이기 전의 초기 취향 벡터를 만들기 위한 레이어입니다. 운영 단계에서는 실제 사용자 interaction이 늘어날수록 AI profile signal의 비중을 낮추는 것이 좋습니다.
