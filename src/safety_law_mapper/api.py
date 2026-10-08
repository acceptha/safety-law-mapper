"""REST API over the matching engine.

The fourth interface onto one engine — CLI, library, MCP, and now HTTP. All
four call `matcher.match()`, and the two server interfaces build their
responses in `view`, so a citation cannot differ depending on how you asked
for it. That sharing is the point: four façades, one source of truth.

Serving choices worth stating:
  - Read-only. Every route is a GET; the dataset is a build artifact that
    changes by pull request, not by HTTP. Nothing here can write.
  - The dataset loads once at import and is cached. Requests touch memory,
    not the filesystem.
  - CORS is wide open because the data is already public (CC BY 4.0) and the
    static demo on GitHub Pages is a different origin. There is no session,
    no credential, and nothing to leak by letting any page read it.
  - Bad input is a 400 that names the valid values; a missing mapping is a
    404 that names real ones. An error a caller cannot act on is a bug.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import DISCLAIMER, __version__
from .view import (
    DEFAULT_LIMIT,
    GROUNDING_RULE,
    MAX_LIMIT,
    categories,
    format_mapping,
    get_dataset,
    search,
)

app = FastAPI(
    title="safety-law-mapper API",
    version=__version__,
    summary="작업 상황으로 적용되는 한국 안전 법령·조항을 찾는 규칙 기반 API",
    description=(
        "작업 상황을 입력하면 적용되는 산업안전보건 법령·조항을 반환합니다.\n\n"
        "모든 조항에 law.go.kr 원문 링크(`source_url`)와 사람이 원문 대조한 날짜"
        "(`verification`)가 실립니다. 미검증 항목은 숨기지 않고 그렇게 표시합니다.\n\n"
        "규칙 기반이며 AI 추론을 쓰지 않습니다. 매핑 데이터에 없는 작업은 빈 결과를 "
        "반환합니다 — 추측하지 않습니다.\n\n"
        f"{DISCLAIMER}"
    ),
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", summary="상태 확인", tags=["meta"])
def health() -> dict[str, Any]:
    """로드된 데이터셋 규모와 버전. 배포 후 데이터가 실제로 실렸는지 확인하는 용도."""
    ds = get_dataset()
    return {
        "status": "ok",
        "version": __version__,
        "laws": len(ds.laws),
        "mappings": len(ds.mappings),
        "articles": sum(
            len(al.articles) for m in ds.mappings.values() for al in m.applicable_laws
        ),
    }


@app.get("/search", summary="작업 상황으로 적용 조항 검색", tags=["search"])
def search_endpoint(
    q: Annotated[
        list[str],
        Query(description="검색 키워드. 반복 지정 가능 (예: ?q=밀폐공간&q=용접)"),
    ] = [],
    category: Annotated[
        str | None, Query(description="작업 분류. /categories가 반환한 값만 허용")
    ] = None,
    employees: Annotated[int | None, Query(ge=1, description="상시근로자 수")] = None,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description=f"최대 결과 수 (최대 {MAX_LIMIT})")
    ] = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """키워드·분류·근로자 수로 적용 법령·조항을 검색합니다.

    `q`와 `category`가 모두 비면 빈 결과를 반환합니다. 결과가 `limit`에 잘리면
    `truncated: true`가 실립니다 — 잘린 목록을 전체 의무로 오해하지 않도록.
    """
    try:
        return search(get_dataset(), q, category, employees, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/categories", summary="작업 분류 목록", tags=["search"])
def categories_endpoint() -> dict[str, Any]:
    """`category` 인자로 쓸 수 있는 값과, 각 분류에 속한 작업 유형.

    예시는 데이터에서 유도되므로 매핑이 추가돼도 이 응답이 낡지 않습니다.
    """
    return categories(get_dataset())


@app.get("/mappings", summary="전체 매핑 목록", tags=["mappings"])
def list_mappings() -> dict[str, Any]:
    """조항 본문 없이 매핑 목록만. 목록 화면에서 전건을 받기 위한 경량 응답."""
    ds = get_dataset()
    return {
        "count": len(ds.mappings),
        "mappings": [
            {
                "mapping_id": m.mapping_id,
                "work_type": m.work_type.name_ko,
                "category": m.work_type.category.value,
                "keywords": list(m.work_type.keywords),
                "article_count": sum(len(al.articles) for al in m.applicable_laws),
            }
            for m in sorted(ds.mappings.values(), key=lambda x: x.mapping_id)
        ],
    }


@app.get("/mappings/{mapping_id}", summary="매핑 상세", tags=["mappings"])
def get_mapping_endpoint(mapping_id: str) -> dict[str, Any]:
    """매핑 ID로 적용 조항 전체를 조회합니다."""
    ds = get_dataset()
    mapping = ds.mappings.get(mapping_id)
    if mapping is None:
        known = sorted(ds.mappings)[:10]
        raise HTTPException(
            status_code=404,
            detail=f"매핑을 찾을 수 없습니다: {mapping_id} (예: {', '.join(known)} ...)",
        )
    payload = format_mapping(mapping, ds.laws)
    payload["grounding"] = GROUNDING_RULE
    payload["disclaimer"] = DISCLAIMER
    return payload


def main() -> None:
    """`slm-serve` 엔트리포인트."""
    import argparse

    import uvicorn

    p = argparse.ArgumentParser(description="safety-law-mapper REST API 서버")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    args = p.parse_args()

    uvicorn.run(
        "safety_law_mapper.api:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
