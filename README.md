# safety-law-mapper (안전법규 매핑 엔진)

**작업 상황을 입력하면 적용되는 한국 안전 법령·조항을 찾아주는 규칙 기반 오픈소스 매핑 엔진**입니다.

기존 법령 검색 도구는 전부 "법령 → 내용" 방향입니다. 이 프로젝트는 **"작업 상황 → 적용 조항"이라는 역방향 매핑**을 구조화된 오픈 데이터(YAML)로 만들고, 이를 검색하는 CLI/라이브러리를 제공합니다.

> ⚠️ **본 도구는 법률 자문이 아닙니다.** 모든 결과는 참고용이며 법적 판단을 대체하지 않습니다.

## 설치

```bash
pip install safety-law-mapper
```

Python 3.11 이상이 필요합니다.

## 사용법

```bash
# 키워드로 적용 법령·조항 검색
slm search 밀폐공간 용접

# 작업 분류·근로자 수 조건 추가
slm search 용접 --category hot-work --employees 30

# 매핑 상세 조회
slm show confined-space-welding

# 데이터 검증 (스키마 + 참조 무결성)
slm validate
```

종료 코드: `0` 정상, `1` 결과 없음, `2` 검증 오류.

## 라이브러리로 사용

```python
from safety_law_mapper.loader import load_dataset
from safety_law_mapper.matcher import Query, match

ds = load_dataset()
results = match(list(ds.mappings.values()), Query(keywords=["밀폐공간", "용접"]))
for r in results:
    print(r.mapping.work_type.name_ko, r.score)
```

## 제품 원칙

- **규칙 기반, AI 추론 배제** — 명시적 데이터로만 답하므로 왜 그 법이 적용되는지 누구나 검증할 수 있습니다.
- **핵심 자산은 코드가 아니라 데이터** — 검증된 상황→조항 매핑은 커뮤니티가 함께 키우는 오픈 데이터입니다.
- **인용은 절대 지어내지 않습니다** — 모든 조항 인용에 `source_url`(law.go.kr) 필수. 미검증 항목은 `last_verified: null`로 표시됩니다.

## 데이터 기여

매핑 데이터 추가 방법은 [CONTRIBUTING.md](docs/CONTRIBUTING.md)를 참고하세요. 템플릿 복사 → 채우기 → `slm validate` → PR, 10분이면 충분합니다.

## 라이선스

- 코드: [MIT](LICENSE)
- 데이터 (`data/`): [CC BY 4.0](LICENSE-DATA)

---

⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.
