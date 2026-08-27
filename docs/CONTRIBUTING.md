# 기여 가이드 — 매핑 데이터 1건 추가하기

이 프로젝트의 핵심 자산은 코드가 아니라 **검증된 매핑 데이터**입니다. 이 문서는 매핑 1건을 추가하는 전 과정을 10분 안에 따라할 수 있게 안내합니다.

## 1. 준비

```bash
git clone https://github.com/acceptha/safety-law-mapper
cd safety-law-mapper
pip install -e ".[dev]"
```

## 2. 템플릿 복사

`data/mappings/` 아래에 새 YAML 파일을 만듭니다. 파일명 = `mapping_id` (kebab-case 영문 슬러그).

```yaml
mapping_id: my-work-type            # 파일명과 동일, 고유해야 함
work_type:
  name_ko: 작업 이름(한국어)
  category: hot-work                 # 아래 통제 어휘 중 하나
  keywords: [키워드1, 키워드2]        # 검색에 쓰일 한국어 키워드
conditions:                          # 모두 선택 사항. 없으면 항상 적용
  min_employees: null
  max_employees: null
  substances: []
  equipment: []
applicable_laws:
  - law_id: osh-rule                 # data/laws/ 에 있는 law_id 여야 함
    articles:
      - article_ref: 제000조          # 형식: 제N조 또는 제N조의M
        article_title: 조문 제목
        obligation_type: general     # 아래 통제 어휘 중 하나
        obligation_subject: employer # 선택: employer|principal-contractor|supervisor|worker|owner
        summary_ko: 의무 내용 한 줄 요약
        valid_from: "2024-01-01"     # 시행일 (필수)
        valid_until: null            # 실효일 (선택)
        source_url: https://www.law.go.kr/법령/...   # 필수 — 반드시 law.go.kr 원문 링크
references: []                       # 선택: KOSHA GUIDE 등
last_verified: null                  # 조문을 직접 대조 확인한 날짜. 미확인이면 null
verified_by: null                    # 확인자 GitHub 핸들
```

### 통제 어휘

- `work_type.category`: `hot-work`, `confined-space`, `work-at-height`, `lifting`, `excavation`, `electrical`, `chemical-handling`, `machinery`, `demolition`, `transport`, `physical-hazard`(소음·고열·한랭·방사선·진동 등 물리적 유해인자)
- `obligation_type`: `general`, `appointment`(선임), `measurement`(측정), `education`(교육), `report`(보고), `permit`(허가), `inspection`(점검), `provision`(지급/설치)

## 3. 철칙 — 인용은 지어내지 않는다

- 모든 조항에 **law.go.kr 원문 `source_url` 필수**입니다.
- 조문 번호·내용을 [국가법령정보센터](https://www.law.go.kr)에서 **직접 대조**한 경우에만 `last_verified`에 날짜를 적습니다.
- 확인하지 못했다면 `last_verified: null`로 두세요. 리뷰 과정에서 사람이 확인합니다.

## 4. 검증

```bash
slm validate      # 스키마 + 참조 무결성 검사
pytest            # 전체 테스트
```

`slm validate`가 통과해야 PR이 병합됩니다 (CI에서 자동 실행).

## 5. PR 제출

- 데이터 PR과 코드 PR은 분리해 주세요.
- 커밋 메시지: Conventional Commits (`data: add forklift-operation mapping`)
- 데이터 PR은 스키마 통과 + 사람 리뷰 1인 이상 후 병합됩니다.

## 코드 기여

- Python ≥3.11, 의존성 추가는 이슈로 먼저 논의해 주세요.
- 매처 동작 변경에는 반드시 테스트가 따라야 합니다.
- 커밋: `feat:`, `fix:`, `data:`, `docs:` prefix 사용.
