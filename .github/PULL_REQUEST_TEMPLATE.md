<!-- 데이터 PR과 코드 PR은 분리해 주세요 -->

## 변경 내용

<!-- 무엇을, 왜 변경했는지 간단히 -->

## 종류

- [ ] 데이터 (매핑/법령 YAML 추가·수정)
- [ ] 코드 (엔진/CLI/테스트)
- [ ] 문서

## 데이터 PR 체크리스트 (해당 시)

- [ ] 모든 조항에 `source_url`(law.go.kr) 포함
- [ ] [국가법령정보센터](https://www.law.go.kr)에서 조문 번호·제목·내용을 **직접 대조**했고 `last_verified`에 날짜 기입 (미대조 시 `null`)
- [ ] `slm validate` 통과
- [ ] `pytest` 통과
- [ ] (권장) `tests/fixtures/golden_queries.yaml`에 쿼리 케이스 추가

## 코드 PR 체크리스트 (해당 시)

- [ ] 매처 동작 변경에 테스트 동반
- [ ] `pytest` 통과
