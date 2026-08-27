# 출품 개요 — safety-law-mapper (안전법규 매핑 엔진)

> **한 줄 요약**: "이 작업에 어떤 법이 적용되는가?" — 작업 상황을 입력하면 적용되는 한국 안전 법령·조항을 찾아주는 규칙 기반 오픈소스 매핑 엔진이자 공개 데이터셋.

## 바로 확인하기

| 채널 | 주소 |
|---|---|
| 🔎 **웹 데모 (설치 불필요)** | https://acceptha.github.io/safety-law-mapper/ |
| 📦 GitHub 저장소 | https://github.com/acceptha/safety-law-mapper |
| 🐍 PyPI (`pip install safety-law-mapper`) | https://pypi.org/project/safety-law-mapper/ |

로컬 실행: 이 zip을 풀고 `pip install -e .` → `slm search 밀폐공간 용접`

## 정량 현황 (v0.2.0, 2026-08-27 기준)

- 매핑 데이터 **30건** / 11개 작업 카테고리 전부 커버 / 조문 인용 118건(고유 94개 조문)
- **전 조문을 국가법령정보센터(law.go.kr) 원문과 대조 검증** — 검증일·검증자를 데이터에 기록(`last_verified`/`verified_by`), 시행일은 부령 연혁판 헤더와 부칙(조항별 유예)까지 확인
- 테스트 23건 + 골든 쿼리 픽스처 36케이스, CI(Python 3.11~3.14) / PyPI 릴리스 2회(v0.1.0, v0.2.0 — 태그 push 시 자동 배포)
- 병합 PR 10건 · 이슈 19건 — **안전관리자 관점 리뷰 → law.go.kr 재검증 → 반영 → 후속 이슈 분리** 사이클이 전부 공개 이력으로 남아 있음

## 무엇이 새로운가

기존 도구(국가법령정보센터, KOSHA 스마트검색)는 전부 "법령 → 내용" 방향 검색입니다. 이 프로젝트는 **"작업 상황 → 적용 조항" 역방향 매핑**을 구조화된 오픈 데이터(YAML, CC BY 4.0)로 만든 첫 시도입니다. AI 추론을 배제한 규칙 기반이므로 모든 결과의 근거가 데이터로 투명하게 검증·수정(PR)될 수 있습니다.

## 어디서 무엇을 보면 되나

| 보고 싶은 것 | 위치 |
|---|---|
| 프로젝트 배경·차별성·아키텍처 | `README.md` |
| 기획 전문 (사회적 기여, 커뮤니티 전략, 로드맵, 리스크) | `안전법규-매핑엔진-기획서.md` |
| 데이터 모델·스코프 결정 이력 | `PROJECT_SPEC.md` |
| 매핑 데이터 (프로젝트의 핵심 자산) | `data/mappings/*.yaml` |
| 매칭 엔진 (순수 함수, 확정 순위 규칙) | `src/safety_law_mapper/matcher.py` |
| 데이터 품질 장치 (스키마+무결성 검증) | `src/safety_law_mapper/validate.py`, `schemas/` |
| 기여 파이프라인 (10분 기여 가이드, 시행일 검증 절차) | `docs/CONTRIBUTING.md` |
| 변경 이력 | `CHANGELOG.md` |
| 현장 실증 사례 | 실제 안전관리자 점검 문서에서 출발한 세차장 매핑(`data/mappings/carwash-operation.yaml`, PR #27), 현장 검증 리뷰로 보강된 용접 매핑(PR #9) — 원본 문서·개인정보는 미포함 |

## 라이선스·면책

- 코드 MIT / 데이터 CC BY 4.0 — 누구나 자유롭게 재사용·파생 가능
- ⚠️ 본 도구의 모든 결과는 참고용이며 법적 판단을 대체하지 않습니다.
