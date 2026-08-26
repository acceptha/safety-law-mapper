# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식과 [유의적 버전](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

### Added
- README 데모, 아키텍처 다이어그램, 기존 도구 비교표
- 커뮤니티 문서: 행동강령, 보안 정책, 이슈·PR 템플릿

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

[Unreleased]: https://github.com/acceptha/safety-law-mapper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/acceptha/safety-law-mapper/releases/tag/v0.1.0
