"""MCP server: exposes the matching engine as tools an LLM can call.

Why this module exists
----------------------
Ask an LLM "밀폐공간 용접 시 법적 의무는?" and it will answer with article
numbers that do not exist. The failure is not that the model is weak — it is
that nothing in the loop can tell a real citation from an invented one.

This server closes that loop. Every article handed back carries the
`source_url` it was verified against and the date a human checked it, and
entries nobody has verified say so in the payload instead of looking like
the rest. The model is told, in the response itself, to cite only what the
response contains.

Design constraints
------------------
  - Reuse `matcher.match()` verbatim. No ranking logic lives here, so the
    golden-query regression suite (tests/fixtures/golden_queries.yaml) covers
    this path too. A second implementation would be a second thing to drift.
  - Formatting is pure functions over a Dataset, kept free of MCPServer so it
    stays testable without the optional `mcp` dependency installed.
  - Token budget is a correctness concern, not a nicety: 34 mappings x 136
    article citations will not fit a prompt. `search_laws` caps results and
    says so when it truncates.
  - Never guess. An empty query returns nothing, matching the matcher's own
    contract — a plausible-looking guess is the exact failure we are here to
    prevent.
"""

from __future__ import annotations

from typing import Any

from . import DISCLAIMER, __version__
from .loader import Dataset, load_dataset
from .matcher import MatchResult, Query, match
from .models import Law, Mapping, WorkCategory

DEFAULT_LIMIT = 5
MAX_LIMIT = 20

UNVERIFIED = "미검증 (사람 검토 필요)"

# Sent back with every result set. The tool output is the only citation
# source the model is allowed to draw on; saying so in-band is what makes
# this a grounding layer rather than just a search API.
GROUNDING_RULE = (
    "조항을 인용할 때는 이 응답에 포함된 article_ref와 source_url만 사용하십시오. "
    "여기에 없는 조항 번호를 생성하거나 추론하지 마십시오. "
    f"verification이 '{UNVERIFIED}'인 항목은 사람 검토 전이므로 그 사실을 함께 알리십시오."
)

_dataset: Dataset | None = None


def get_dataset() -> Dataset:
    """Load the dataset once and reuse it; the server is long-running."""
    global _dataset
    if _dataset is None:
        _dataset = load_dataset()
    return _dataset


# --- formatting (pure) ---------------------------------------------------


def _law_name(laws: dict[str, Law], law_id: str) -> str:
    law = laws.get(law_id)
    return law.name_ko if law else law_id


def format_mapping(mapping: Mapping, laws: dict[str, Law]) -> dict[str, Any]:
    """One mapping as a citation-bearing record.

    `source_url` is non-optional in the schema, so every article here can be
    traced back to law.go.kr by whoever reads the answer.
    """
    articles: list[dict[str, Any]] = []
    for al in mapping.applicable_laws:
        for art in al.articles:
            articles.append(
                {
                    "law_id": al.law_id,
                    "law": _law_name(laws, al.law_id),
                    "article_ref": art.article_ref,
                    "article_title": art.article_title,
                    "obligation_type": art.obligation_type.value,
                    "obligation_subject": (
                        art.obligation_subject.value if art.obligation_subject else None
                    ),
                    "summary_ko": art.summary_ko,
                    "source_url": art.source_url,
                }
            )
    return {
        "mapping_id": mapping.mapping_id,
        "work_type": mapping.work_type.name_ko,
        "category": mapping.work_type.category.value,
        "keywords": list(mapping.work_type.keywords),
        "verification": (
            mapping.last_verified.isoformat() if mapping.last_verified else UNVERIFIED
        ),
        "article_count": len(articles),
        "articles": articles,
    }


def format_results(
    results: list[MatchResult],
    laws: dict[str, Law],
    limit: int,
) -> dict[str, Any]:
    """Rank-ordered results, capped, with the grounding rule attached."""
    shown = results[:limit]
    payload: dict[str, Any] = {
        "result_count": len(shown),
        "total_matched": len(results),
        "truncated": len(results) > len(shown),
        "grounding": GROUNDING_RULE,
        "disclaimer": DISCLAIMER,
        "results": [],
    }
    for r in shown:
        entry = format_mapping(r.mapping, laws)
        entry["match"] = {
            "category_match": r.category_match,
            "keyword_score": r.keyword_score,
            "specificity": r.specificity,
        }
        payload["results"].append(entry)
    return payload


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(int(limit), MAX_LIMIT))


def search(
    ds: Dataset,
    keywords: list[str] | None = None,
    category: str | None = None,
    employees: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run a query against the dataset. Raises ValueError on a bad category."""
    cat: WorkCategory | None = None
    if category:
        try:
            cat = WorkCategory(category)
        except ValueError:
            valid = ", ".join(c.value for c in WorkCategory)
            raise ValueError(f"알 수 없는 분류 '{category}'. 가능한 값: {valid}") from None
    query = Query(keywords=list(keywords or []), category=cat, employees=employees)
    results = match(list(ds.mappings.values()), query)
    return format_results(results, ds.laws, clamp_limit(limit))


def categories(ds: Dataset) -> dict[str, Any]:
    """The controlled vocabulary, with the work types that live under each.

    Examples come from the data rather than a hand-written gloss, so this
    cannot drift from what `search_laws(category=...)` will actually accept.
    """
    buckets: dict[str, list[str]] = {c.value: [] for c in WorkCategory}
    for m in ds.mappings.values():
        buckets[m.work_type.category.value].append(m.work_type.name_ko)
    return {
        "categories": [
            {"category": k, "work_types": sorted(v), "mapping_count": len(v)}
            for k, v in buckets.items()
        ]
    }


# --- MCP wiring ----------------------------------------------------------


def build_server() -> Any:
    """Construct the MCPServer. Imported lazily so the module above stays
    usable (and testable) without the optional `mcp` dependency.

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
