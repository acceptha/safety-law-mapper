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
    DROWNED = "익사"
    OTHER = "기타"


# Longest-first so '쓰러짐' is not shadowed by a shorter overlapping term.
_ACCIDENT_TERMS = sorted(
    (t for t in AccidentType if t is not AccidentType.OTHER),
    key=lambda t: -len(t.value),
)


class SiteType(str, Enum):
    """업종·현장 구분. 사고속보 300건에 실제로 나타난 표현에서 귀납한 어휘."""

    CONSTRUCTION = "건설현장"
    MANUFACTURING = "제조업"
    AGRICULTURE = "농림축산"
    LOGISTICS = "창고·물류"
    WASTE = "환경·폐기물"
    FACILITY = "건물·시설"
    SERVICE = "서비스·판매"
    OTHER = "기타"


# 순서가 곧 우선순위. '제조업 사업장 내 야적장'은 제조업으로 본다.
_SITE_RULES: tuple[tuple[SiteType, tuple[str, ...]], ...] = (
    (SiteType.CONSTRUCTION, ("공사", "건설", "신축", "증축", "토목", "철도")),
    (SiteType.MANUFACTURING, ("제조", "공장", "조선소", "플랜트", "발전소", "정제", "정미소")),
    (SiteType.AGRICULTURE, (
        "축사", "농장", "벌목", "야산", "임야", "과수", "양식", "산림", "조림",
        "휴양림", "양돈", "양계", "농로",
    )),
    (SiteType.LOGISTICS, ("창고", "물류", "야적", "하치", "적치", "하역", "부두", "차고지")),
    (SiteType.WASTE, ("폐기물", "재활용", "매립", "선별", "하수", "정수", "배수장")),
    (SiteType.FACILITY, (
        "아파트", "건물", "주택", "상가", "학교", "병원", "골프장", "옥상",
        "빌딩", "호텔", "주차",
    )),
    (SiteType.SERVICE, ("마트", "도매", "소매", "서비스업", "세탁", "음식", "숙박")),
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
    site_type: SiteType | None = None
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
_SITE_SOJAE_RE = re.compile(r"소재\s*(.+?)\s*(?:에서|$)", re.M)
_SITE_FALLBACK_RE = re.compile(r"^(.+?)에서", re.M)
# '경남 창원시', '울산 남구', '전라북도 군산시' 같은 지역 접두어를 떼어낸다.
_REGION_PREFIX_RE = re.compile(r"^\S+\s+\S*[시군구]\s+|^\S*[시군구]\s+")
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


def site_phrase(body: str) -> str | None:
    """The '…에서' phrase naming where the accident happened, region stripped.

    Most posts read '<지역> 소재 <현장>에서'; a minority drop '소재' entirely,
    so we fall back to the first '…에서' clause and remove the region prefix.
    """
    m = _SITE_SOJAE_RE.search(body)
    if m:
        phrase = m.group(1).strip()
    else:
        m = _SITE_FALLBACK_RE.search(body)
        if not m:
            return None
        phrase = _REGION_PREFIX_RE.sub("", m.group(1).strip()).strip()
    return phrase or None


def parse_site_type(body: str) -> SiteType | None:
    """Classify the site phrase into controlled vocabulary.

    We store the category, never the source phrase — same rule as
    `work_keywords` (기획서 §6.1).
    """
    phrase = site_phrase(body)
    if phrase is None:
        return None
    for site_type, terms in _SITE_RULES:
        if any(t in phrase for t in terms):
            return site_type
    return SiteType.OTHER


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


def scrub_region(text: str, region: str | None) -> str:
    """Drop region names before keyword extraction.

    Place names swallow work terms — '인천 연수구' contains '수구', '마포구'
    contains '포구' — and a district name is never a work signal, so removing
    it can only help.
    """
    if not region:
        return text
    for token in region.split():
        if token:
            text = text.replace(token, " ")
    return text


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
    region = parse_region(title)
    return Incident(
        pst_no=pst_no,
        posted_at=posted_at,
        occurred_at=parse_occurred_at(body, posted_at),
        region=region,
        site_type=parse_site_type(body),
        accident_type=parse_accident_types(text),
        fatalities=int(fatal.group(1)) if fatal else None,
        fall_height_m=float(height.group(1)) if height else None,
        work_keywords=extract_keywords(
            scrub_region(text, region), lexicon, mapping_keywords
        ),
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


def _fall_first(incident: Incident, results: list[MatchResult]) -> list[MatchResult]:
    """추락 사망 사고에서는 추락 방호 매핑을 앞으로 끌어올린다.

    매처는 '무슨 작업을 하고 있었나'로만 순위를 매긴다. 그래서 지붕 철거 중
    떨어진 사망 사고가 `demolition-work` 를, 작업발판 위 용접 중 떨어진
    사망 사고가 `welding-cutting` 을 1순위로 받았다. 둘 다 실제로 하던
    작업이지만, **사람이 죽은 경위는 추락**이고 그걸 규정하는 것은 제42·43조와
    각 설비의 추락 방호 조문이다. 수집분에 이런 사고가 17건 있었다.

    사고 유형은 사고의 사실이지 질의어가 아니므로, 매처(`match`)는 건드리지
    않는다. `slm search` 와 MCP 는 사고 유형을 모르고, 알 필요도 없다.

    **정확히 일치한 키워드가 있는 매핑만 올린다.** 부분 일치까지 올리면
    `리프트` 가 `테이블리프트`·`시저리프트` 에 삼켜져 화물용 승강기 추락이
    고소작업대(제186조)로 간다 — 근거가 약한 쪽이 강한 쪽을 밀어내는 셈이다.
    화물용 승강기는 양중기이지 고소작업대가 아니다.

    같은 묶음 안의 순서는 매처가 매긴 그대로 둔다.
    """
    if AccidentType.FALL not in (incident.accident_type or []):
        return results
    spoken = set(incident.work_keywords)
    lifted, rest = [], []
    for result in results:
        work_type = result.mapping.work_type
        exact = spoken & set(work_type.keywords)
        (lifted if work_type.category == WorkCategory.WORK_AT_HEIGHT and exact else rest).append(
            result
        )
    return lifted + rest


def map_incident(incident: Incident, mappings: list[Mapping]) -> IncidentMatch:
    """Rank mappings that apply to this incident's work type.

    An incident with no extracted keywords matches nothing — the matcher
    never guesses, and neither do we.
    """
    if not incident.work_keywords:
        return IncidentMatch(incident=incident, results=[])
    results = match(mappings, Query(keywords=list(incident.work_keywords)))
    return IncidentMatch(incident=incident, results=_fall_first(incident, results))


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
