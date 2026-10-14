# REST API

매칭 엔진을 HTTP로 노출합니다. CLI·라이브러리·MCP와 **같은 엔진, 같은 응답 형식**입니다.

> ⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.

## 실행

```bash
pip install "safety-law-mapper[api]"
slm-serve                      # http://127.0.0.1:8000
slm-serve --host 0.0.0.0 --port 8080
slm-serve --reload             # 개발용
```

대화형 문서는 `/docs` (Swagger UI), 스키마는 `/openapi.json`에 있습니다.

### Docker

```bash
docker build -t safety-law-mapper .
docker run --rm -p 8000:8000 safety-law-mapper
```

이미지에 데이터가 포함되며, **빌드 중 `slm validate`가 실행**됩니다. 데이터가 깨지면 운영이 아니라 빌드가 실패합니다. 컨테이너는 비루트(uid 10001)로 실행되고 `/health` 기반 HEALTHCHECK가 붙어 있습니다.

## 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | 상태 + 로드된 데이터 규모 |
| `GET` | `/search` | 작업 상황으로 적용 조항 검색 |
| `GET` | `/categories` | 작업 분류 목록 |
| `GET` | `/mappings` | 전체 매핑 목록 (조항 본문 제외) |
| `GET` | `/mappings/{mapping_id}` | 매핑 상세 |

**전 경로가 GET입니다.** 데이터셋은 PR로 바뀌는 빌드 산출물이며 HTTP로 쓰지 않습니다. 이 불변식은 테스트로 고정돼 있습니다 (`test_every_route_is_read_only`).

### `GET /search`

| 쿼리 | 타입 | 설명 |
|---|---|---|
| `q` | `str[]` | 검색 키워드. 반복 지정 (`?q=밀폐공간&q=용접`) |
| `category` | `str?` | 작업 분류. `/categories`가 반환한 값만 |
| `employees` | `int?` | 상시근로자 수 (≥1) |
| `limit` | `int` | 기본 5, 최대 20 |

```bash
curl "http://127.0.0.1:8000/search?q=밀폐공간&q=용접&limit=2"
```

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

`q`와 `category`가 모두 비면 **빈 결과**입니다 — 추측하지 않습니다.

`truncated`는 편의 필드가 아닙니다. 이것을 보지 못한 호출자는 잘린 목록을 **적용 의무 전체로 오해**합니다.

## 상태 코드

| 코드 | 상황 | 응답 |
|---|---|---|
| `400` | 알 수 없는 `category` | 가능한 값 전체를 나열 |
| `404` | 없는 `mapping_id` | 실재하는 ID 예시를 나열 |
| `422` | `limit` 범위 밖 등 타입 위반 | FastAPI 검증 오류 |
| `405` | GET 외 메서드 | — |

호출자가 **행동으로 옮길 수 없는 에러 메시지는 버그**로 취급합니다. 400과 404는 무엇을 넣어야 했는지 함께 돌려줍니다.

```bash
$ curl "http://127.0.0.1:8000/search?q=test&category=nonsense"
{"detail":"알 수 없는 분류 'nonsense'. 가능한 값: hot-work, confined-space, ... forestry"}
```

## 설계 메모

### 네 번째 인터페이스, 하나의 엔진

CLI · 라이브러리 · MCP · REST가 모두 `matcher.match()`를 호출하고, 두 서버 인터페이스는 `view` 모듈에서 응답을 만듭니다. **어떻게 물었는지에 따라 인용이 달라질 수 없습니다.**

이 불변식은 말이 아니라 테스트입니다:

```python
def test_rest_and_mcp_return_identical_payloads():
    direct    = search(get_dataset(), ["밀폐공간", "용접"], limit=5)
    over_http = client.get("/search", params={...}).json()
    assert over_http == direct
```

누군가 한쪽을 재구현하면 이 테스트가 깨집니다. 그게 공용 레이어를 둔 이유입니다.

### 읽기 전용

데이터는 PR로 리뷰되고 CI가 검증해야 머지됩니다. HTTP로 쓸 수 있게 만들면 그 게이트를 우회하는 경로가 생깁니다. 쓰기 경로를 아예 만들지 않았습니다.

### CORS 전면 개방

데이터가 이미 공개(CC BY 4.0)이고, 정적 데모가 GitHub Pages라는 다른 오리진에서 돕니다. 세션도 자격증명도 없어 **다른 페이지가 읽어서 샐 것이 없습니다.** `allow_credentials=False`로 못박아 뒀습니다.

### 데이터셋은 한 번만 로드

`view.get_dataset()`이 캐시합니다. 요청은 파일시스템이 아니라 메모리를 봅니다.

### 웹 데모는 두 모드로 동작한다

`slm-serve`는 `web/`을 같은 오리진에 서빙합니다. 페이지는 부팅할 때 `/health`를 한 번 찔러 보고,

- **응답하면** → `GET /search`를 호출합니다. 실제 Python 엔진이 답합니다.
- **응답하지 않으면** (GitHub Pages) → 번들된 `data.json`과 `web/matcher.js`로 답합니다.

덕분에 데모는 서버 없이도 살아 있고, 서버가 있으면 엔진이 하나로 수렴합니다. 두 모드가 같은 결과를 내는지는 아래 파리티 테스트가 지킵니다.

### JS 포트의 드리프트를 테스트로 막는다

오프라인 데모 요구 때문에 매칭 로직이 JavaScript로 한 번 더 구현돼 있습니다. 중복을 없앨 수 없다면, **어긋남을 검출 가능하게** 만들어야 합니다.

`tests/test_web_parity.py`가 골든 쿼리 전건을 Node와 Python 양쪽에 돌려 결과 순서가 같은지 비교합니다. 동점이 반드시 발생하는 분류 단독 질의도 별도로 넣었습니다 — 이전 인라인 구현은 동점 처리에 `localeCompare`(로케일 정렬)를 써서 Python의 코드포인트 정렬과 어긋날 수 있었고, 그 결함이 이 테스트를 만들게 된 계기입니다.

## 한계

- 인증·레이트리밋이 없습니다. 공개 데이터 읽기 전용이라 현재는 불필요하지만, 공개 배포 시 역프록시 레벨의 레이트리밋을 권장합니다.
- 페이지네이션은 `limit`뿐이며 오프셋이 없습니다. 전건이 필요하면 `/mappings` 후 개별 조회를 쓰십시오.
- 조항 **해석**은 하지 않습니다. 적용 가능한 조항과 근거 링크를 반환할 뿐입니다.
