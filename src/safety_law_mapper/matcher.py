"""Condition-matching engine. Pure functions only — no I/O.

Ranking (confirmed 2026-08-26):
  1. exact category match
  2. keyword hit count
  3. condition specificity (number of non-empty conditions on the entry)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Conditions, Mapping, WorkCategory


@dataclass(frozen=True)
class Query:
    keywords: list[str] = field(default_factory=list)
    category: WorkCategory | None = None
    employees: int | None = None
    substances: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MatchResult:
    mapping: Mapping
    category_match: bool
    keyword_hits: int
    specificity: int

    @property
    def score(self) -> tuple[int, int, int]:
        return (int(self.category_match), self.keyword_hits, self.specificity)


def _conditions_allow(cond: Conditions, query: Query) -> bool:
    """A mapping is excluded only when the query explicitly contradicts its conditions.

    Absent query fields never exclude — we only return what data explicitly encodes,
    and an unknown query field means "no constraint given".
    """
    if query.employees is not None:
        if cond.min_employees is not None and query.employees < cond.min_employees:
            return False
        if cond.max_employees is not None and query.employees > cond.max_employees:
            return False
    if query.substances and cond.substances:
        if not set(query.substances) & set(cond.substances):
            return False
    if query.equipment and cond.equipment:
        if not set(query.equipment) & set(cond.equipment):
            return False
    return True


def _keyword_hits(mapping: Mapping, query_keywords: list[str]) -> int:
    hits = 0
    entry_keywords = mapping.work_type.keywords
    for qk in query_keywords:
        if any(qk in ek or ek in qk for ek in entry_keywords):
            hits += 1
        elif qk in mapping.work_type.name_ko:
            hits += 1
    return hits


def _specificity(cond: Conditions) -> int:
    n = 0
    if cond.min_employees is not None:
        n += 1
    if cond.max_employees is not None:
        n += 1
    n += len(cond.substances)
    n += len(cond.equipment)
    return n


def match(mappings: list[Mapping], query: Query) -> list[MatchResult]:
    """Return ranked matches. A mapping matches if it has at least one positive
    signal (category match or keyword hit) and its conditions don't exclude the query.
    A query with no keywords and no category matches nothing (never guess)."""
    results: list[MatchResult] = []
    for m in mappings:
        if not _conditions_allow(m.conditions, query):
            continue
        category_match = query.category is not None and m.work_type.category == query.category
        keyword_hits = _keyword_hits(m, query.keywords) if query.keywords else 0
        if not category_match and keyword_hits == 0:
            continue
        results.append(
            MatchResult(
                mapping=m,
                category_match=category_match,
                keyword_hits=keyword_hits,
                specificity=_specificity(m.conditions),
            )
        )
    results.sort(key=lambda r: (-r.score[0], -r.score[1], -r.score[2], r.mapping.mapping_id))
    return results
