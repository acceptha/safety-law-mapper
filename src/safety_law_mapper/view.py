"""Presentation layer shared by every non-CLI interface.

The MCP server and the REST API answer the same questions, so they answer
them with the same bytes: both build their payloads here. A second
formatter would be a second thing to drift, and a citation that differs
between interfaces is a citation nobody can trust.

Pure functions over a Dataset — no FastAPI, no MCPServer, no I/O beyond the
one cached dataset load. That is what lets both interfaces be tested without
either dependency installed.
"""

from __future__ import annotations

from typing import Any

from . import DISCLAIMER
from .loader import Dataset, load_dataset
from .matcher import MatchResult, Query, match
from .models import Law, Mapping, WorkCategory

DEFAULT_LIMIT = 5
MAX_LIMIT = 20

UNVERIFIED = "미검증 (사람 검토 필요)"

# Sent back with every result set. The payload is the only citation source a
# caller is allowed to draw on; saying so in-band is what makes this a
# grounding layer rather than just a search API.
GROUNDING_RULE = (
    "조항을 인용할 때는 이 응답에 포함된 article_ref와 source_url만 사용하십시오. "
    "여기에 없는 조항 번호를 생성하거나 추론하지 마십시오. "
    f"verification이 '{UNVERIFIED}'인 항목은 사람 검토 전이므로 그 사실을 함께 알리십시오."
)

_dataset: Dataset | None = None


def get_dataset() -> Dataset:
    """Load the dataset once and reuse it; both servers are long-running."""
    global _dataset
    if _dataset is None:
        _dataset = load_dataset()
    return _dataset


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
    """Rank-ordered results, capped, with the grounding rule attached.

    `truncated` is not a nicety: a caller that cannot see it will read a
    capped list as the complete set of duties that apply.
    """
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


def parse_category(category: str | None) -> WorkCategory | None:
    """Raises ValueError naming the valid values — callers surface that text
    to whoever got it wrong, human or model."""
    if not category:
        return None
    try:
        return WorkCategory(category)
    except ValueError:
        valid = ", ".join(c.value for c in WorkCategory)
        raise ValueError(f"알 수 없는 분류 '{category}'. 가능한 값: {valid}") from None


def search(
    ds: Dataset,
    keywords: list[str] | None = None,
    category: str | None = None,
    employees: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run a query against the dataset. Raises ValueError on a bad category."""
    query = Query(
        keywords=list(keywords or []),
        category=parse_category(category),
        employees=employees,
    )
    results = match(list(ds.mappings.values()), query)
    return format_results(results, ds.laws, clamp_limit(limit))


def categories(ds: Dataset) -> dict[str, Any]:
    """The controlled vocabulary, with the work types that live under each.

    Examples come from the data rather than a hand-written gloss, so this
    cannot drift from what a category filter will actually accept.
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
