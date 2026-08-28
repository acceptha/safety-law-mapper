"""KOSHA 사고속보 records: parsing, keyword extraction, and gap detection.

Pure functions and models only — no network I/O. Fetching lives in
`scripts/fetch_kosha_incidents.py` so this module stays offline-testable.

Design constraints (docs/사고속보-연계-기획서.md):
  - Never assert that an incident *violated* an article. We report the
    articles that apply to the work type, not fault.
  - Gap detection MUST go through matcher.match(); a plain substring scan
    reports gaps that do not exist (see 기획서 §4.5).
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .matcher import MatchResult, Query, match
from .models import Mapping, Url, WorkCategory

BBS_ID = "B2025021314108"
POST_URL = (
    "https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2"
    f"?bbsId={BBS_ID}&pstNo={{pst_no}}"
)


class AccidentType(str, Enum):
    FALL = "떨어짐"
    CRUSHED = "깔림"
    CAUGHT = "끼임"
    STRUCK = "맞음"
    COLLISION = "부딪힘"
    TRIP = "넘어짐"
    COLLAPSE_PERSON = "쓰러짐"
    ELECTRIC_SHOCK = "감전"
    BURN = "화상"
    ASPHYXIA = "질식"
    COLLAPSE = "붕괴"
    BURIAL = "매몰"
    FIRE = "화재"
    EXPLOSION = "폭발"
    DROWNING = "빠짐"
    OTHER = "기타"


# Longest-first so '쓰러짐' is not shadowed by a shorter overlapping term.
_ACCIDENT_TERMS = sorted(
    (t for t in AccidentType if t is not AccidentType.OTHER),
    key=lambda t: -len(t.value),
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Incident(_StrictModel):
    """One 사고속보 post, reduced to facts plus our own vocabulary.

    `title` is optional on purpose: KOSHA posts carry no 공공누리 mark, so
    storing the headline verbatim is a judgement call the repo owner makes
    (see data/incidents/README.md). Everything else here is either a bare
    fact (date, region, fatalities) or a term from our own lexicon.
    """

    pst_no: str
    posted_at: datetime.date
    occurred_at: datetime.datetime | None = None
    region: str | None = None
    site_type: str | None = None
    accident_type: list[AccidentType] = Field(default_factory=list)
    fatalities: int | None = None
    fall_height_m: float | None = None
    work_keywords: list[str] = Field(default_factory=list)
    source_url: Url
    fetched_at: datetime.date
    title: str | None = None


class LexiconTerm(_StrictModel):
    surface: list[str]
    keywords: list[str] = Field(default_factory=list)
    suppress: list[str] = Field(default_factory=list)
    category: WorkCategory | None = None
    note: str | None = None


class Lexicon(_StrictModel):
    terms: list[LexiconTerm] = Field(default_factory=list)
    stopwords: list[str] = Field(default_factory=list)


def default_incidents_dir() -> Path:
    from .loader import default_data_dir

    return default_data_dir() / "incidents"


def load_lexicon(path: Path | None = None) -> Lexicon:
    path = path or (default_incidents_dir() / "lexicon.yaml")
    if not path.is_file():
        return Lexicon()
    with path.open(encoding="utf-8") as f:
        return Lexicon.model_validate(yaml.safe_load(f) or {})


def load_incidents(path: Path | None = None) -> list[Incident]:
    """Read the append-only JSONL store. Missing file yields an empty list."""
    path = path or (default_incidents_dir() / "kosha-alerts.jsonl")
    if not path.is_file():
        return []
    out: list[Incident] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Incident.model_validate_json(line))
    return out


def write_incidents(incidents: list[Incident], path: Path) -> None:
    """Rewrite the store, sorted newest first, one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(incidents, key=lambda i: (i.posted_at, i.pst_no), reverse=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for inc in ordered:
            f.write(inc.model_dump_json(exclude_none=True) + "\n")


# --- parsing -------------------------------------------------------------

_TITLE_RE = re.compile(r"^\s*\[\s*(\d{1,2})\s*/\s*(\d{1,2})\s*,?\s*([^\]]*?)\s*\]")
_DATE_RE = re.compile(r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})")
_TIME_RE = re.compile(r"(\d{1,2})\s*:\s*(\d{2})")
_SITE_RE = re.compile(r"소재\s*(\S+?)\s*에서")
_FATAL_RE = re.compile(r"사망\s*(\d+)\s*명")
_HEIGHT_RE = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*m\s*\)", re.IGNORECASE)


def strip_html(html: str | None) -> str:
    """Collapse KOSHA's per-character span markup back into readable text."""
    if not html:
        return ""
    import html as html_mod

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def parse_region(title: str) -> str | None:
    m = _TITLE_RE.match(title)
    if not m:
        return None
    region = m.group(3).strip()
    return region or None


def parse_occurred_at(body: str, posted_at: datetime.date) -> datetime.datetime | None:
    m = _DATE_RE.search(body)
    if not m:
        return None
    try:
        day = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    if day > posted_at:  # a parse that lands in the future is a misread
        return None
    tm = _TIME_RE.search(body, m.end())
    if tm and int(tm.group(1)) < 24 and int(tm.group(2)) < 60:
        return datetime.datetime(day.year, day.month, day.day, int(tm.group(1)), int(tm.group(2)))
    return datetime.datetime(day.year, day.month, day.day)


def parse_accident_types(text: str) -> list[AccidentType]:
    return [t for t in _ACCIDENT_TERMS if t.value in text]


def extract_keywords(text: str, lexicon: Lexicon, mapping_keywords: set[str]) -> list[str]:
    """Map raw incident text onto our own controlled vocabulary.

    Only terms we already own are emitted — lexicon targets and mapping
    keywords — so the stored record carries no verbatim source wording.
    Stopwords are dropped because generic verbs like '제거'/'설치' matched
    unrelated mappings (기획서 §4.3).

    Korean compounds swallow shorter keywords ('가용접' contains '용접'), so a
    lexicon entry may `suppress` a keyword the surrounding word does not
    actually mean. Suppression wins over extraction.
    """
    stop = set(lexicon.stopwords)
    found: set[str] = set()
    absorbers: dict[str, list[str]] = {}
    for term in lexicon.terms:
        hits = [s for s in term.surface if s in text]
        if not hits:
            continue
        found.update(k for k in term.keywords if k not in stop)
        for k in term.suppress:
            absorbers.setdefault(k, []).extend(hits)
    found.update(k for k in mapping_keywords if k not in stop and k in text)
    return sorted(k for k in found if not _fully_absorbed(text, k, absorbers.get(k, [])))


def _fully_absorbed(text: str, keyword: str, surfaces: list[str]) -> bool:
    """True when every occurrence of `keyword` sits inside a suppressing compound.

    A text that says both '용접 작업' and '가용접된 러그' keeps 용접 — only the
    case where the compound accounts for all occurrences is suppressed.
    """
    if not surfaces:
        return False
    total = text.count(keyword)
    absorbed = sum(text.count(s) * s.count(keyword) for s in surfaces)
    return total > 0 and absorbed >= total


def build_incident(
    *,
    pst_no: str,
    title: str,
    body: str,
    posted_at: datetime.date,
    fetched_at: datetime.date,
    lexicon: Lexicon,
    mapping_keywords: set[str],
    store_title: bool = True,
) -> Incident:
    """Assemble one record from raw post text. Pure — callers do the fetching."""
    text = f"{title}\n{body}"
    fatal = _FATAL_RE.search(text)
    height = _HEIGHT_RE.search(text)
    site = _SITE_RE.search(body)
    return Incident(
        pst_no=pst_no,
        posted_at=posted_at,
        occurred_at=parse_occurred_at(body, posted_at),
        region=parse_region(title),
        site_type=site.group(1) if site else None,
        accident_type=parse_accident_types(text),
        fatalities=int(fatal.group(1)) if fatal else None,
        fall_height_m=float(height.group(1)) if height else None,
        work_keywords=extract_keywords(text, lexicon, mapping_keywords),
        source_url=POST_URL.format(pst_no=pst_no),
        fetched_at=fetched_at,
        title=title if store_title else None,
    )


# --- mapping -------------------------------------------------------------


@dataclass(frozen=True)
class IncidentMatch:
    incident: Incident
    results: list[MatchResult]

    @property
    def is_gap(self) -> bool:
        return not self.results


def map_incident(incident: Incident, mappings: list[Mapping]) -> IncidentMatch:
    """Rank mappings that apply to this incident's work type.

    An incident with no extracted keywords matches nothing — the matcher
    never guesses, and neither do we.
    """
    if not incident.work_keywords:
        return IncidentMatch(incident=incident, results=[])
    results = match(mappings, Query(keywords=list(incident.work_keywords)))
    return IncidentMatch(incident=incident, results=results)


def map_incidents(incidents: list[Incident], mappings: list[Mapping]) -> list[IncidentMatch]:
    return [map_incident(i, mappings) for i in incidents]


def gap_terms(matches: list[IncidentMatch]) -> list[tuple[str, int]]:
    """Frequency of accident types among unmapped incidents, most common first.

    This is the contribution queue: what the data cannot answer yet.
    """
    counts: dict[str, int] = {}
    for m in matches:
        if not m.is_gap:
            continue
        for t in m.incident.accident_type or [AccidentType.OTHER]:
            counts[t.value] = counts.get(t.value, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def coverage(matches: list[IncidentMatch]) -> tuple[int, int]:
    """Return (mapped, total)."""
    return sum(1 for m in matches if not m.is_gap), len(matches)
