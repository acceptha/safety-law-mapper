# PROJECT_SPEC.md — Safety Law Mapper (안전법규 매핑 엔진)

> Machine-oriented spec for Claude Code. Human-readable companion: `안전법규-매핑엔진-기획서.md`
> Version: 0.3 | Date: 2026-08-26 (open questions 1,2,3,4,5,7 RESOLVED — see §7)

## 0. ⛔ SCOPE GUARD — READ FIRST

**Implement Phase 1 ONLY.** Phase 2 (checklist generator) and Phase 3 (law-change tracker) are documented below for schema-design context but **MUST NOT be implemented yet**. Do not create modules, CLI commands, or dependencies for Phase 2/3. If a task seems to require them, stop and ask the user.

## 1. Project Identity

- **Name**: `safety-law-mapper` — CONFIRMED by user (2026-07-15). Do not rename.
- **Purpose**: Rule-based mapping from work situations (작업 상황) to applicable Korean safety laws/articles (적용 법령·조항)
- **Type**: Open-source monorepo — open data (YAML) + Python CLI/library
- **License**: MIT (code), CC BY 4.0 (data) — pending user confirmation
- **Language**: Data and user-facing strings in Korean; code identifiers, comments, commit messages in English
- **Not a legal advisory tool**: Every output must include a disclaimer (참고용, 법적 판단 대체 불가)

## 2. Repository Layout (target)

```
safety-law-mapper/
├── data/
│   ├── laws/            # Law registry: one YAML per law
│   └── mappings/        # Mapping entries: one YAML per work-type
├── schemas/             # JSON Schema files for data validation
│   ├── law.schema.json
│   └── mapping.schema.json
├── src/safety_law_mapper/
│   ├── __init__.py
│   ├── models.py        # dataclasses/pydantic models mirroring schemas
│   ├── loader.py        # load + parse YAML data
│   ├── matcher.py       # condition-matching engine (pure functions)
│   ├── cli.py           # CLI entrypoint
│   └── validate.py      # data validation (schema + referential integrity)
├── tests/
├── docs/
│   └── CONTRIBUTING.md  # data contribution guide (Korean)
├── pyproject.toml
└── README.md            # Korean, include disclaimer
```

## 3. Data Model

### 3.1 Law registry entry (`data/laws/*.yaml`)

```yaml
law_id: osh-act                    # slug, unique
name_ko: 산업안전보건법
name_short: 산안법
type: act                          # act | decree | rule | notice(고시)
administered_by: 고용노동부
source_url: https://www.law.go.kr/법령/산업안전보건법
```

### 3.2 Mapping entry (`data/mappings/*.yaml`)

```yaml
mapping_id: confined-space-welding          # slug, unique
work_type:
  name_ko: 밀폐공간 용접
  category: hot-work                        # controlled vocabulary, see 3.3
  keywords: [밀폐공간, 용접, 화기작업]        # for keyword search
conditions:                                  # ALL optional; absent = always applies
  min_employees: null                        # int | null
  max_employees: null
  substances: []                             # controlled substance slugs
  equipment: [welding-machine]
applicable_laws:
  - law_id: osh-rule                         # FK -> law registry
    articles:
      - article_ref: "제618조"               # formal article number
        article_title: 정의
        obligation_type: general             # see 3.4 — REQUIRED for Phase 2 compat
        obligation_subject: employer         # OPTIONAL/nullable — employer|principal-contractor|supervisor|worker|owner (Q4 resolved)
        summary_ko: 밀폐공간 정의 및 적용 범위
        valid_from: "2024-01-01"             # REQUIRED for Phase 3 compat (Q5: replaced effective_date)
        valid_until: null                    # OPTIONAL, null = currently in force
        source_url: https://www.law.go.kr/...
references:                                  # optional, e.g., KOSHA guides
  - title: KOSHA GUIDE H-119
    url: https://...
last_verified: "2026-07-15"                  # date a human last checked this entry
verified_by: null                            # GitHub handle, optional
```

### 3.3 `work_type.category` controlled vocabulary (extensible via PR)

`hot-work`, `confined-space`, `work-at-height`, `lifting`, `excavation`, `electrical`, `chemical-handling`, `machinery`, `demolition`, `transport`

### 3.4 `obligation_type` controlled vocabulary

`general`, `appointment`(선임), `measurement`(측정), `education`(교육), `report`(보고), `permit`(허가), `inspection`(점검), `provision`(지급/설치)

> `obligation_type` and `conditions.min_employees` exist NOW so Phase 2 can consume them LATER. Populate them in data; do not build features on them yet.

## 4. Phase 1 Deliverables (BUILD THESE)

| # | Deliverable | Acceptance criteria |
|---|---|---|
| 1 | JSON Schemas (`schemas/`) | Validate examples in §3; enum-enforce vocabularies |
| 2 | Models + loader | Round-trip: YAML → model → dict equals source |
| 3 | Matcher | Given query {keywords?, category?, employees?, substances?, equipment?} returns ranked mapping entries; ranking criteria TBD (see §7 open Q7); pure function; unit-tested; golden query fixtures ("this query MUST include 제619조") |
| 4 | CLI | `slm search <키워드>`, `slm show <mapping_id>`, `slm validate` ; Korean output; exit codes: 0 ok, 1 no result, 2 validation error |
| 5 | Validation | Schema check + referential integrity (law_id FKs, unique slugs, valid dates) + golden query fixtures ; all run in CI (GitHub Actions) |
| 6 | Seed data | ≥20 mapping entries for high-risk work types (밀폐공간, 고소작업, 용접, 지게차, 크레인, 굴착 등), 산안법+산업안전보건기준규칙 중심; include ≥1 composite case (e.g. 밀폐공간+용접) to validate condition composition |
| 7 | Docs | README.md (Korean, with disclaimer), CONTRIBUTING.md (data contribution workflow) |
| 8 | Packaging & distribution | PyPI package `safety-law-mapper` (`pip install` → `slm`), data bundled in Phase 1; GitHub Actions release on git tag via PyPI trusted publishing |

### Implementation constraints

- Python ≥3.11, minimal deps: `pydantic`, `pyyaml`, `click` (or `typer`), `jsonschema`. No web frameworks, no DB, no LLM/AI dependencies.
- Matching is deterministic rule-based. Never infer applicability; only return what data explicitly encodes.
- Every CLI output ends with: `⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.`
- Law citations must never be fabricated. Seed data articles must carry `source_url`; if uncertain during data authoring, mark entry `last_verified: null` and flag for human review.

## 5. Phase 2 — Checklist Generator [DO NOT IMPLEMENT]

> Status: **PLANNED. NOT approved for implementation. Do not build.**

Future intent, for schema-compat awareness only:

- Input: workplace profile (업종, 상시근로자 수, 취급물질, 설비) → output: obligation checklist (PDF/XLSX)
- Will consume `obligation_type` + `conditions.*` from Phase 1 mappings
- Will likely add `data/obligations/` with due-frequency fields (매년/반기/상시)
- Design implication for Phase 1: keep `conditions` matcher logic in a reusable pure module (`matcher.py`), not embedded in CLI

## 6. Phase 3 — Law Change Tracker [DO NOT IMPLEMENT]

> Status: **PLANNED. NOT approved for implementation. Do not build.**

Future intent, for schema-compat awareness only:

- Monitor 국가법령정보센터 Open API for amendments; diff changed articles; notify (Slack/email) which mapping entries are affected
- Requires stable article identity: hence `article_ref` + `effective_date` + `law_id` in Phase 1 schema — keep these fields mandatory and well-formed
- Will likely version law texts in-repo (git-tracked snapshots)
- Design implication for Phase 1: never store article text inline as source of truth; store refs + URLs

## 7. Conventions for Claude Code

- Read this file before any implementation session. Respect the SCOPE GUARD (§0).
- Tests: pytest; every matcher behavior change requires a test.
- Data PRs and code PRs should be separate commits.
- When adding seed data, cite `source_url` from law.go.kr; if a citation can't be verified, ask the user instead of guessing.
- Commit style: Conventional Commits (`feat:`, `fix:`, `data:`, `docs:`).
- Open questions — RESOLVED 2026-08-26 with user:
  - (1) License: code MIT / data CC BY 4.0. ✅
  - (2) CLI name: `slm` confirmed — PyPI package name `safety-law-mapper` free; unrelated `slm` package exists on PyPI but no console-script/command collision. ✅
  - (3) Framework: `typer`. ✅
  - (4) `obligation_subject` added NOW as optional/nullable field. ✅
  - (5) `effective_date` replaced by `valid_from` (required) + `valid_until` (optional, default null). ✅
  - (7) Ranking: category-exact-match > keyword-hit-count > condition-specificity; deterministic tie-break by mapping_id. ✅
  - (6) STILL OPEN (decidable during implementation): law.go.kr/KOSHA API article-existence verification in CI — defer decision to Phase 2/3 unless data quality issues arise.
