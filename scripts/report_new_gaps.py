#!/usr/bin/env python
"""오늘 수집분 중 **미매핑인 사고만** 골라 이슈 본문을 만든다.

Usage: python scripts/report_new_gaps.py [--date YYYY-MM-DD]

출력이 비면 알릴 것이 없다는 뜻이다. 호출부는 빈 출력을 보고 이슈를 만들지
않는다.

왜 '새 사고'가 아니라 '새 공백'인가. 사고는 주 2~3건씩 들어오지만 대부분은
이미 맞는 조문으로 간다. 들어올 때마다 알리면 두 주 만에 아무도 보지 않게
되고, 그러면 정작 손이 필요한 날의 알림도 같이 묻힌다. 실제로 사람이 할 일이
생기는 것은 새 사고가 어떤 조문도 가리키지 못할 때뿐이다.

`--date` 의 기본값은 오늘(UTC)이고, 이는 수집기가 `fetched_at` 에 적는 값과
같은 기준이다. **수집 직후에 돌리는 것을 전제로 한다** — 며칠 지나서 돌리면
그날 수집분이 없으니 아무것도 나오지 않는다.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from safety_law_mapper.incidents import (  # noqa: E402
    Incident,
    load_incidents,
    map_incidents,
)
from safety_law_mapper.loader import load_dataset  # noqa: E402

STRUCTURE = REPO_ROOT / "tests" / "fixtures" / "osh-rule-structure-2026-10-14.json"
LAW_ID = "osh-rule"
#: 이슈 본문에 띄울 '비어 있는 절'의 개수. 전체 목록은 법령 커버리지 리포트에
#: 있고, 여기서는 새 사고를 어디에 넣을지 짚는 단서로만 쓴다.
EMPTY_SECTION_LIMIT = 5
#: 조문이 이보다 적은 절은 비어 있다고 보고하지 않는다 — 대개 우리가 다룰 일이
#: 없는 특수 설비다. `build_law_coverage_report.py` 와 같은 기준.
MIN_SECTION = 3

# 사고속보 제목은 "[8/19, 부산 강서구] 이동식 비계가…" 꼴이다. 링크 라벨 안의
# 대괄호는 마크다운이 첫 ']' 에서 링크 텍스트를 끊어 링크를 깨뜨린다.
_TITLE_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]\s*")


def _blob_url(path: str) -> str:
    """이슈 본문의 상대 링크는 저장소 파일로 풀리지 않는다. 절대 주소를 쓴다."""
    slug = os.environ.get("GITHUB_REPOSITORY") or "acceptha/safety-law-mapper"
    return f"https://github.com/{slug}/blob/main/{urllib.parse.quote(path)}"


def _link_label(title: str | None) -> str:
    if not title:
        return "(제목 미보관)"
    return _TITLE_PREFIX_RE.sub("", title).replace("[", "(").replace("]", ")")


def new_gaps(
    incidents: list[Incident], mappings: list, on: datetime.date
) -> list[Incident]:
    """`on` 에 수집된 사고 중 어떤 매핑도 받지 못한 것."""
    fresh = [i for i in incidents if i.fetched_at == on]
    return [m.incident for m in map_incidents(fresh, mappings) if m.is_gap]


def empty_sections(mappings: list) -> list[tuple[int, str, str]]:
    """(조문 수, 위치, 범위) — 매핑이 하나도 없는 절, 큰 것부터."""
    if not STRUCTURE.exists():
        return []
    covered = {
        article.article_ref
        for mapping in mappings
        for law in mapping.applicable_laws
        if law.law_id == LAW_ID
        for article in law.articles
    }
    found = []
    for section in json.loads(STRUCTURE.read_text(encoding="utf-8")):
        articles = section["articles"]
        if len(articles) < MIN_SECTION or any(a in covered for a in articles):
            continue
        where = " / ".join(x for x in (section["chapter"], section["section"]) if x)
        found.append((len(articles), where or section["part"], f"{articles[0]}~{articles[-1]}"))
    return sorted(found, key=lambda row: -row[0])


def render(gaps: list[Incident], sections: list[tuple[int, str, str]]) -> str:
    if not gaps:
        return ""
    lines = [
        f"오늘 수집분 중 **{len(gaps)}건**이 어떤 조문도 가리키지 못했습니다.",
        "",
        "| 발생 | 지역 | 업종 | 사고 |",
        "|---|---|---|---|",
    ]
    for inc in gaps:
        when = inc.occurred_at.date().isoformat() if inc.occurred_at else "-"
        site = inc.site_type.value if inc.site_type else "-"
        lines.append(
            f"| {when} | {inc.region or '-'} | {site} | "
            f"[{_link_label(inc.title)}]({inc.source_url}) |"
        )

    if sections:
        lines += [
            "",
            "## 아직 비어 있는 절",
            "",
            "규칙에서 아직 조문을 하나도 싣지 못한 절입니다. 위 사고가 여기 속할 수도, "
            "아닐 수도 있습니다 — 먼저 대조해 볼 목록일 뿐입니다. 전체는 "
            f"[법령 커버리지 리포트]({_blob_url('docs/법령-커버리지.md')})에 있습니다.",
            "",
            "| 조문 수 | 위치 | 범위 |",
            "|---:|---|---|",
        ]
        for count, where, span in sections[:EMPTY_SECTION_LIMIT]:
            lines.append(f"| {count} | {where} | {span} |")

    lines += [
        "",
        "## 작업 지시",
        "",
        "아래를 Claude Code 에 그대로 붙여넣으면 됩니다.",
        "",
        "```",
        "위 사고들의 원문을 읽고, 산업안전보건기준에 관한 규칙에서 해당 작업에",
        "적용되는 조문을 찾아 매핑을 추가해 줘. 다음을 지켜야 한다:",
        "",
        "- 조문은 law.go.kr 원문으로 직접 확인한다. 추측해서 쓰지 않는다",
        "- 해당 사고가 그 조문을 위반했다고 단정하지 않는다",
        "- 새 매핑을 넣은 뒤 상위 3순위를 재어, 기존 사고의 순위가 틀어지지",
        "  않았는지 확인한다 (넓은 매핑이 키워드를 쥐고 있으면 회수까지 필요하다)",
        "- 조문이 없는 사고라면 없다고 보고하고 억지로 넣지 않는다",
        "```",
        "",
        "조문이 이 규칙 밖(교통·선박 등)이면 **닫고 기록만 남깁니다.** "
        "억지로 매핑을 만들면 정밀도가 떨어집니다.",
        "",
        "---",
        "",
        "이 이슈는 `scripts/report_new_gaps.py` 가 자동 생성했습니다.",
        "",
        "⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다. "
        "사고속보는 조사 전 신고 단계 정보입니다.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--date",
        type=datetime.date.fromisoformat,
        default=datetime.date.today(),
        help="이 날짜에 수집된 기록만 본다 (기본: 오늘)",
    )
    args = ap.parse_args()

    dataset = load_dataset()
    body = render(
        new_gaps(load_incidents(), list(dataset.mappings.values()), args.date),
        empty_sections(list(dataset.mappings.values())),
    )
    if body:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
