"""MCP server: exposes the matching engine as tools an LLM can call.

Why this module exists
----------------------
Ask an LLM "밀폐공간 용접 시 법적 의무는?" and it will answer with article
numbers it cannot back. The failure is not that the model is weak — it is
that nothing in the loop can tell a real citation from a remembered one.
Measured on this dataset, 42% of a tool-less answer's citations were
verifiable; through this server it is 100% (docs/MCP-grounding-실측.md).

This module is only the MCP wiring. Everything it returns is built by
`view`, which the REST API shares, so the two interfaces cannot disagree
about what a citation looks like.

Design constraints
------------------
  - Reuse `matcher.match()` verbatim. No ranking logic lives here, so the
    golden-query regression suite covers this path too.
  - Import `mcp` lazily, inside `build_server()`. The package is an optional
    extra and the rest of the tree must import without it.
  - Never guess. An empty query returns nothing, matching the matcher's own
    contract — a plausible-looking guess is the exact failure we prevent.
"""

from __future__ import annotations

from typing import Any

from . import DISCLAIMER, __version__
from .view import (
    DEFAULT_LIMIT,
    GROUNDING_RULE,
    categories,
    format_mapping,
    get_dataset,
    search,
)


def build_server() -> Any:
    """Construct the MCPServer.

    The pure layer raises ValueError; this layer translates it to ToolError.
    The SDK treats anything else as a crash and replaces the message with
    "Error executing tool <name>" — which would hide the very text (the list
    of valid categories, the known mapping ids) the model needs to correct
    its own call.
    """
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError

    mcp = MCPServer(
        name="safety-law-mapper",
        version=__version__,
        instructions=(
            "한국 산업안전보건 법령에서 '작업 상황 → 적용 조항'을 찾는 도구입니다.\n"
            "작업 내용·설비·위험요인에 대해 법적 의무를 묻는 질문을 받으면 "
            "반드시 search_laws를 먼저 호출하고, 그 응답에 담긴 조항만 인용하십시오.\n"
            "도구가 결과를 반환하지 않으면 '해당 작업에 대한 매핑 데이터가 아직 없다'고 "
            "답하십시오. 조항을 추측해서는 안 됩니다.\n"
            f"{DISCLAIMER}"
        ),
    )

    @mcp.tool(
        name="search_laws",
        description=(
            "작업 상황으로 적용 법령·조항을 검색합니다. 각 조항은 law.go.kr 원문 링크"
            "(source_url)와 사람이 검증한 날짜를 함께 반환합니다. "
            "keywords는 작업·설비·위험요인을 나타내는 한국어 단어입니다 (예: ['밀폐공간','용접']). "
            "category는 list_categories가 반환한 값만 사용하십시오. "
            "keywords와 category가 모두 비면 결과가 없습니다 — 추측하지 않습니다."
        ),
    )
    def search_laws(
        keywords: list[str] | None = None,
        category: str | None = None,
        employees: int | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        try:
            return search(get_dataset(), keywords, category, employees, limit)
        except ValueError as e:
            raise ToolError(str(e)) from e

    @mcp.tool(
        name="get_mapping",
        description=(
            "매핑 ID로 적용 조항 전체를 조회합니다. search_laws 결과의 mapping_id를 "
            "사용하십시오 (예: 'confined-space-welding')."
        ),
    )
    def get_mapping(mapping_id: str) -> dict[str, Any]:
        ds = get_dataset()
        mapping = ds.mappings.get(mapping_id)
        if mapping is None:
            known = ", ".join(sorted(ds.mappings)[:10])
            raise ToolError(f"매핑을 찾을 수 없습니다: {mapping_id} (예: {known} ...)")
        payload = format_mapping(mapping, ds.laws)
        payload["grounding"] = GROUNDING_RULE
        payload["disclaimer"] = DISCLAIMER
        return payload

    @mcp.tool(
        name="list_categories",
        description=(
            "search_laws의 category 인자로 쓸 수 있는 작업 분류 목록과, 각 분류에 "
            "속한 작업 유형을 반환합니다. 분류명을 추측하기 전에 호출하십시오."
        ),
    )
    def list_categories() -> dict[str, Any]:
        return categories(get_dataset())

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
