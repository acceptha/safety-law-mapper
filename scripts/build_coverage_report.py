"""Render docs/incidents/coverage.md from the incident store.

Usage: python scripts/build_coverage_report.py [output.md]

The report carries no wall-clock timestamp on purpose: a generated-at line
would change on every scheduled run and produce a commit even when nothing
was collected. Everything here is derived from the data, so an unchanged
store renders an unchanged file and the daily job stays silent.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safety_law_mapper.incidents import (  # noqa: E402
    AccidentType,
    IncidentMatch,
    load_incidents,
    map_incidents,
)
from safety_law_mapper.loader import load_dataset  # noqa: E402

GAP_LIST_LIMIT = 25

# 사고속보 제목은 "[8/19, 부산 강서구] 이동식 비계가…" 꼴이다. 앞의 대괄호는
# 발생일·지역 열과 중복인 데다, 링크 라벨 안에 들어가면 마크다운이 첫 ']'에서
# 링크 텍스트를 끊어 링크가 깨진다.
_TITLE_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]\s*")


def _link_label(title: str | None) -> str:
    if not title:
        return "(제목 미보관)"
    return _TITLE_PREFIX_RE.sub("", title).replace("[", "(").replace("]", ")")


def _bar(ratio: float, width: int = 16) -> str:
    return "█" * round(ratio * width)


def _section_sector(matches: list[IncidentMatch]) -> list[str]:
    agg: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for m in matches:
        key = m.incident.site_type.value if m.incident.site_type else "(미상)"
        agg[key][1] += 1
        if not m.is_gap:
            agg[key][0] += 1
    rows = ["| 업종 | 매핑 | 전체 | 커버리지 |", "|---|---:|---:|---|"]
    for key, (ok, total) in sorted(agg.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
        rows.append(f"| {key} | {ok} | {total} | {ok / total * 100:.0f}% {_bar(ok / total)} |")
    return rows


def _section_accident(matches: list[IncidentMatch]) -> list[str]:
    counts: collections.Counter[str] = collections.Counter()
    gaps: collections.Counter[str] = collections.Counter()
    for m in matches:
        for t in m.incident.accident_type or [AccidentType.OTHER]:
            counts[t.value] += 1
            if m.is_gap:
                gaps[t.value] += 1
    rows = ["| 사고 유형 | 건수 | 미매핑 |", "|---|---:|---:|"]
    for name, n in counts.most_common():
        rows.append(f"| {name} | {n} | {gaps[name]} |")
    return rows


def _section_gaps(matches: list[IncidentMatch]) -> list[str]:
    gaps = sorted(
        (m.incident for m in matches if m.is_gap),
        key=lambda i: i.posted_at,
        reverse=True,
    )
    if not gaps:
        return ["미매핑 사고가 없습니다."]
    out = [
        f"미매핑 **{len(gaps)}건** 중 최근 {min(len(gaps), GAP_LIST_LIMIT)}건입니다."
        " 각 항목이 곧 매핑 기여 대상입니다.",
        "",
        "| 발생 | 지역 | 업종 | 사고 |",
        "|---|---|---|---|",
    ]
    for inc in gaps[:GAP_LIST_LIMIT]:
        when = inc.occurred_at.date().isoformat() if inc.occurred_at else str(inc.posted_at)
        site = inc.site_type.value if inc.site_type else "-"
        label = _link_label(inc.title)
        out.append(f"| {when} | {inc.region or '-'} | {site} | [{label}]({inc.source_url}) |")
    return out


def build(data_dir: Path | None = None) -> str:
    dataset = load_dataset(data_dir)
    incidents = load_incidents()
    matches = map_incidents(incidents, list(dataset.mappings.values()))
    mapped = sum(1 for m in matches if not m.is_gap)
    total = len(matches)
    latest = max((i.posted_at for i in incidents), default=None)
    earliest = min((i.posted_at for i in incidents), default=None)

    lines = [
        "# 사고속보 커버리지 리포트",
        "",
        "> 이 파일은 `scripts/build_coverage_report.py`가 생성합니다. 직접 수정하지 마세요.",
        "> 설계 근거: [사고속보 연계 기획서](../사고속보-연계-기획서.md)",
        "",
        "⚠️ 아래는 **해당 작업 유형에 적용되는 조항**을 찾았는지에 대한 집계입니다.",
        "개별 사고의 법령 위반 여부를 뜻하지 않습니다. 사고속보는 조사 전 신고 단계 정보입니다.",
        "",
        "## 요약",
        "",
        f"- 수집 사고: **{total}건** (게시일 {earliest} ~ {latest})",
        f"- 매핑 데이터: **{len(dataset.mappings)}종**",
        f"- 커버리지: **{mapped}/{total} = {mapped / total * 100:.0f}%**" if total else "- 커버리지: 데이터 없음",
        "",
        "## 업종별 커버리지",
        "",
        *_section_sector(matches),
        "",
        "## 사고 유형별 분포",
        "",
        *_section_accident(matches),
        "",
        "## 데이터 공백 큐",
        "",
        *_section_gaps(matches),
        "",
        "---",
        "",
        "출처: 안전보건공단 산업안전포털 [사고속보](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2)",
        "",
        "⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/incidents/coverage.md")
    text = build()
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = out.read_text(encoding="utf-8") if out.is_file() else None
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{'unchanged' if previous == text else 'wrote'} {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
