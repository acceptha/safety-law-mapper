# MCP 서버 — LLM이 법을 지어내지 않게 만들기

`slm-mcp`는 매칭 엔진을 [Model Context Protocol](https://modelcontextprotocol.io) 툴로 노출합니다. LLM이 안전 법규 질문을 받으면 조항을 **생성**하는 대신 이 도구를 **호출**하고, 사람이 원문 대조한 조항과 law.go.kr 링크만 인용하게 됩니다.

> ⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.

## 왜 필요한가

LLM에 "밀폐공간 용접 시 법적 의무는?"이라고 물으면 그럴듯한 조항 번호를 만들어냅니다. 문제는 모델이 약해서가 아니라, **진짜 인용과 지어낸 인용을 구분할 수 있는 장치가 루프 안에 없다는 것**입니다.

이 서버가 그 루프를 닫습니다.

| 장치 | 내용 |
|---|---|
| `source_url` | 모든 조항에 law.go.kr 원문 링크. 스키마에서 필수 — 근거 없는 데이터는 애초에 머지되지 않음 |
| `verification` | 사람이 원문 대조한 날짜. 미검증 항목은 `"미검증 (사람 검토 필요)"`로 표시되어 숨겨지지 않음 |
| `grounding` | 모든 응답에 동봉되는 인용 규칙 — "이 응답에 없는 조항 번호를 생성하지 말 것" |
| 빈 질의 = 빈 결과 | 키워드·분류가 모두 없으면 아무것도 반환하지 않음. 그럴듯한 추측이 바로 우리가 막으려는 실패 |

## 설치

```bash
pip install "safety-law-mapper[mcp]"
```

## 연결

### Claude Code

```bash
claude mcp add safety-law-mapper -- slm-mcp
```

### Claude Desktop / 기타 MCP 클라이언트

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "safety-law-mapper": {
      "command": "slm-mcp"
    }
  }
}
```

전송 방식은 stdio입니다.

## 툴

### `search_laws`

작업 상황으로 적용 법령·조항을 검색합니다.

| 인자 | 타입 | 설명 |
|---|---|---|
| `keywords` | `list[str]` | 작업·설비·위험요인 한국어 단어 (예: `["밀폐공간","용접"]`) |
| `category` | `str?` | 작업 분류. `list_categories`가 반환한 값만 사용 |
| `employees` | `int?` | 상시근로자 수 |
| `limit` | `int` | 기본 5, 최대 20 |

응답 (요약):

```json
{
  "result_count": 2,
  "total_matched": 4,
  "truncated": true,
  "grounding": "조항을 인용할 때는 이 응답에 포함된 article_ref와 source_url만 사용하십시오. ...",
  "disclaimer": "⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.",
  "results": [
    {
      "mapping_id": "confined-space-welding",
      "work_type": "밀폐공간 용접",
      "category": "confined-space",
      "verification": "2026-08-27",
      "article_count": 8,
      "match": { "category_match": false, "keyword_score": 4, "specificity": 1 },
      "articles": [
        {
          "law_id": "osh-rule",
          "law": "산업안전보건기준에 관한 규칙",
          "article_ref": "제619조",
          "article_title": "밀폐공간 작업 프로그램의 수립·시행",
          "obligation_type": "general",
          "obligation_subject": "employer",
          "summary_ko": "밀폐공간 작업 전 작업 프로그램 수립·시행 (용접 병행 시에도 적용)",
          "source_url": "https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제619조"
        }
      ]
    }
  ]
}
```

### `get_mapping`

`mapping_id`로 적용 조항 전체를 조회합니다. `search_laws`가 `limit`으로 잘라낸 나머지를 마저 볼 때 씁니다.

### `list_categories`

`category` 인자로 쓸 수 있는 분류 목록과, 각 분류에 속한 작업 유형을 반환합니다. 예시는 **데이터에서 유도**되므로 매핑이 추가돼도 문서가 낡지 않습니다.

## 설계 메모

### 매칭 로직을 새로 쓰지 않았다

`matcher.match()`를 그대로 호출합니다. 랭킹 로직이 여기 없으므로 **골든 쿼리 회귀 스위트가 MCP 경로까지 함께 보증**합니다. 두 번째 구현은 두 번째로 어긋날 물건입니다.

### 포맷은 순수 함수

`format_mapping` / `format_results` / `search` / `categories`는 `MCPServer`를 모릅니다. `mcp` 패키지 없이도 테스트되고, MCP 등록부는 얇은 껍데기입니다.

### 토큰 예산은 정확성 문제다

매핑 35종 × 조항 140여 건을 다 보내면 프롬프트에 들어가지 않습니다. `search_laws`는 결과를 자르고 `truncated: true`로 **잘렸다는 사실 자체를 알립니다** — 모델이 "이게 전부"라고 오해하지 않도록.

### 에러는 `ToolError`로 던진다

MCP SDK는 `ToolError`가 아닌 예외를 크래시로 간주하고 메시지를 `Error executing tool <name>`으로 덮어씁니다. 그러면 모델은 **무엇이 잘못됐는지 모른 채** 같은 실수를 반복합니다.

순수 레이어는 `ValueError`를 던지고, MCP 레이어가 `ToolError`로 번역합니다. 그 결과 모델은 교정에 필요한 정보를 그대로 받습니다:

```
Error executing tool search_laws: 알 수 없는 분류 'nonsense'.
가능한 값: hot-work, confined-space, work-at-height, lifting, excavation,
electrical, chemical-handling, machinery, demolition, transport,
physical-hazard, forestry
```

## 한계

- 조항 **해석**은 하지 않습니다. 적용 가능한 조항 목록과 근거 링크를 반환할 뿐이며, 판단은 사람의 몫입니다.
- 매핑 데이터에 없는 작업은 결과가 비어 있습니다. 추측하지 않는 것이 설계이고, 공백은 [good first issue](https://github.com/acceptha/safety-law-mapper/issues)로 열려 있습니다.
- 위반 여부를 판정하지 않습니다.
