#!/usr/bin/env python
r"""규칙의 어느 절이 아직 매핑되지 않았는지 세어 docs/법령-커버리지.md 를 만든다.

사고 커버리지(`docs/incidents/coverage.md`)는 "들어온 사고 중 몇 건을 받았나"를
센다. 이 리포트는 반대쪽을 센다 — "법이 요구하는 것 중 우리가 아직 말하지 못하는
것은 어디인가".

두 질문은 다른 답을 낸다. 달비계 사망 7건은 사고 커버리지에서 내내 **매핑됨**
이었다. 비계 조립작업(제56~58조)으로 가고 있었기 때문이다. 정작 그 사고를
규정하는 제63조는 어떤 매핑에도 없었고, 그 사실은 이 리포트에서만 보였다.

절 구조는 `tests/fixtures/osh-rule-structure-*.json` 스냅샷에서 읽는다. 법령
본문이 law.go.kr 의 iframe 안에서 다시 로드되는 구조라 받아오지 않는다. 법이
개정되면 사람이 다시 떠야 하고, 파일명의 날짜가 그 시점이다.

    (() => window.frames[0].document.body.innerText)()

위를 브라우저에서 실행해 저장한 뒤 이렇게 자른다.

1. 좌측 목차를 버린다. 목차에도 `제N조(제목)` 이 한 번씩 나오고 제목이
   '...' 로 잘려 있어, 먼저 나온다는 이유로 그걸 집으면 절 이름이 잘린다.
   본문은 `제1편` 으로 시작하는 **마지막** 줄부터다.
2. 부칙 앞에서 멈춘다. 부칙에도 `제1조(시행일)` 같은 조문이 있다.
3. 편/장/절 머리와 `제N조(` 를 순서대로 읽어 절마다 조문을 모은다.

    python scripts/build_law_coverage_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = REPO_ROOT / "tests" / "fixtures" / "osh-rule-structure-2026-10-14.json"
OUT = REPO_ROOT / "docs" / "법령-커버리지.md"
LAW_ID = "osh-rule"
#: 이보다 작은 절은 "비어 있다"고 보고하지 않는다. 조문 한둘짜리 절은
#: 우리가 다루지 않는 특수 설비인 경우가 대부분이라 목록만 길어진다.
MIN_SECTION = 3


def covered_articles(mappings_dir: Path) -> dict[str, list[str]]:
    """조문 → 그 조문을 싣고 있는 mapping_id 목록."""
    by_article: dict[str, list[str]] = {}
    for path in sorted(mappings_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for law in data["applicable_laws"]:
            if law["law_id"] != LAW_ID:
                continue
            for article in law["articles"]:
                by_article.setdefault(article["article_ref"], []).append(data["mapping_id"])
    return by_article


def render(sections: list[dict], by_article: dict[str, list[str]]) -> str:
    total = sum(len(s["articles"]) for s in sections)
    hit = sum(1 for s in sections for a in s["articles"] if a in by_article)

    lines = [
        "# 법령 커버리지 리포트",
        "",
        "산업안전보건기준에 관한 규칙의 어느 절을 아직 다루지 못하고 있는지 보여줍니다.",
        "",
        f"- 조문: **{hit}/{total}**",
        f"- 절: **{len(sections)}개** 중 조문이 하나라도 매핑된 절 "
        f"**{sum(1 for s in sections if any(a in by_article for a in s['articles']))}개**",
        "",
        "> 이 숫자를 올리는 것 자체는 목표가 아닙니다. 규칙에는 우리가 다룰 일이 없는",
        "> 특수 설비·물질 조항이 많습니다. 이 리포트의 쓸모는 **사고가 실제로 일어나는데",
        "> 조문이 비어 있는 곳**을 찾는 데 있습니다.",
        "",
        "## 비어 있는 절",
        "",
        f"조문 {MIN_SECTION}개 이상인 절 중 매핑이 하나도 없는 곳입니다.",
        "",
        "| 조문 수 | 위치 | 범위 |",
        "|---:|---|---|",
    ]
    for s in sections:
        if len(s["articles"]) < MIN_SECTION:
            continue
        if any(a in by_article for a in s["articles"]):
            continue
        where = " / ".join(x for x in (s["chapter"], s["section"]) if x) or s["part"]
        span = f"{s['articles'][0]}~{s['articles'][-1]}"
        lines.append(f"| {len(s['articles'])} | {where} | {span} |")

    lines += ["", "## 일부만 다루는 절", "", "| 다룸 | 위치 | 아직 없는 조문 |", "|---|---|---|"]
    for s in sections:
        hits = [a for a in s["articles"] if a in by_article]
        if not hits or len(hits) == len(s["articles"]):
            continue
        where = " / ".join(x for x in (s["chapter"], s["section"]) if x) or s["part"]
        missing = [a for a in s["articles"] if a not in by_article]
        shown = ", ".join(missing[:8]) + (f" 외 {len(missing) - 8}건" if len(missing) > 8 else "")
        lines.append(f"| {len(hits)}/{len(s['articles'])} | {where} | {shown} |")

    lines += [
        "",
        "---",
        "",
        "생성: `python scripts/build_law_coverage_report.py`",
        "",
        "⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    sections = json.loads(STRUCTURE.read_text(encoding="utf-8"))
    by_article = covered_articles(REPO_ROOT / "data" / "mappings")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(sections, by_article), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
