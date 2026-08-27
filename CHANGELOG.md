# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식과 [유의적 버전](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

## [0.2.0] - 2026-08-27

### Added
- 매핑 8건 추가 (총 **29건**, 11개 카테고리): 굴착기(2022년 신설 전용 조항 포함), 도장, 석면 해체(의무주체 `owner` 첫 사용), 산업용 로봇, 항타기·항발기, 타워크레인 설치·해체(2개 법령 교차 인용), 소음(85dB 정의·소음 감소 조치 포함), 고열·폭염(**2025년 폭염 신설 규정** — 체감온도 33도 이상 매 2시간 20분 휴식 반영)
- `work_type.category` 통제 어휘에 `physical-hazard` 추가 — 소음·고열·방사선 등 물리적 유해인자 작업 (#7)
- 안전관리자 관점 현장 검증 리뷰 반영 — 용접 매핑에 제620·623·629·240조 등 누락 의무 보강 (#9, #12, #14)
- README 데모, 아키텍처 다이어그램, 기존 도구 비교표
- 커뮤니티 문서: 행동강령, 보안 정책, 이슈·PR 템플릿

### Changed
- 매칭 엔진: 키워드 정확일치(2점)를 부분일치·작업명 매치(1점)보다 우선하는 가중 랭킹 (#11)
- **BREAKING**: 라이브러리 API의 `MatchResult.keyword_hits` 필드를 `keyword_score`로 개명

### Fixed
- **`valid_from` 전수 감사** (#16): 공포일로 기재됐던 시행일 정정(부령 제273호 2020-01-16), 부칙 조항별 유예 반영(제179·442조 2021-01-16, 굴착기 제221조의2~4 2023-07-01), `valid_from` 의미를 "summary가 서술하는 의무의 시행일"로 정의하고 CONTRIBUTING에 검증 절차 문서화

## [0.1.0] - 2026-08-26

### Added
- 매핑 데이터 21건 — 고위험 작업 유형, 10개 카테고리 전부 커버, 전 조항 law.go.kr 원문 대조 검증 (`last_verified` 기록)
  - 조합 케이스(밀폐공간×용접), 2개 법령 교차 인용 케이스(위험물질: 산안법+기준규칙) 포함
- 매칭 엔진: 카테고리 정확 일치 > 키워드 일치 수 > 조건 특이도 순위, 결정적 tie-break, 순수 함수
- CLI: `slm search / show / validate / version` — 한국어 출력, 면책 문구 고정, 종료 코드 규약(0/1/2)
- 데이터 검증: JSON Schema + 참조 무결성(법령 FK, 슬러그 중복, 날짜 구간) + 골든 쿼리 회귀 픽스처 23케이스
- JSON Schema 2종 (법령 레지스트리, 매핑 엔트리) — 통제 어휘 enum 강제
- pydantic 모델 + YAML 로더 (무손실 왕복 보장)
- GitHub Actions CI (Python 3.11–3.14) 및 태그 릴리스 자동화 (PyPI trusted publishing)
- 문서: README(한국어, 면책 포함), CONTRIBUTING(10분 기여 가이드)

[Unreleased]: https://github.com/acceptha/safety-law-mapper/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/acceptha/safety-law-mapper/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/acceptha/safety-law-mapper/releases/tag/v0.1.0
