#!/usr/bin/env python
"""쌓인 신규 사고를 묶어 요약 본문을 만든다. 보낼 때가 아니면 아무것도 내지 않는다.

Usage: python scripts/report_new_incidents.py --since YYYY-MM-DD [--today YYYY-MM-DD]

`--since` 는 마지막으로 보낸 날이다. 호출부는 그 날짜를 저장소가 아니라 **실제로
보내진 것**(요약 이슈의 마지막 댓글 시각)에서 읽는다. 상태 파일을 두지 않으므로
발송이 한 번 실패해도 다음 실행에 그대로 남아 있고, 커밋도 늘지 않는다.

정책은 소급 측정으로 정했다 — `scripts/simulate_alert_policies.py`. 수집분
347건(59주)에 각 정책을 적용한 결과다.

    수집될 때마다        1.96/주   3.0건   최악 지연  1일
    8건 쌓이면           0.61/주   9.6건   최악 지연 20일   ← 조용한 달에 묵는다
    8건 또는 7일         0.76/주   7.6건   최악 지연  8일   ← 채택
    매주 월요일          1.00/주   5.9건   최악 지연  7일

순수 개수 임계값은 함정이다. 게시가 몰려 있어(415일 중 116일만 게시, 간격 최대
10일) 조용한 구간에서는 8건이 차는 데 3주가 걸린다. 일수 상한을 같이 걸어야
한다. 반대로 매주 고정은 조용한 주에도 울린다.

**공백 알림(`report_new_gaps.py`)과 역할이 다르다.** 그쪽은 손이 필요한 날 즉시
울리고(주 0.32회, 100% 유효), 이쪽은 '무슨 일이 있었나'를 묶어 전한다. 섞으면
둘 다 못 쓰게 된다.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from safety_law_mapper.incidents import (  # noqa: E402
    Incident,
    load_incidents,
    map_incidents,
)
from safety_law_mapper.loader import load_dataset  # noqa: E402

#: 이만큼 쌓이면 보낸다.
THRESHOLD = 8
#: 덜 쌓여도 이만큼 지나면 보낸다. 둘 중 먼저 걸리는 쪽.
MAX_AGE_DAYS = 7
#: 표에 싣는 최대 줄 수. 넘으면 나머지는 건수만 적는다.
TABLE_LIMIT = 20

MENTION = "@acceptha"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from report_new_gaps import _link_label  # noqa: E402


def pending_since(incidents: list[Incident], since: datetime.date) -> list[Incident]:
    """`since` **다음날 이후**에 수집된 사고. 경계일은 이미 보냈으므로 뺀다."""
    return sorted(
        (i for i in incidents if i.fetched_at > since),
        key=lambda i: (i.posted_at, i.pst_no),
        reverse=True,
    )


def should_send(pending: list[Incident], since: datetime.date, today: datetime.date) -> bool:
    if not pending:
        return False
    return len(pending) >= THRESHOLD or (today - since).days >= MAX_AGE_DAYS


def render(pending: list[Incident], mappings: list, since: datetime.date, today: datetime.date) -> str:
    if not should_send(pending, since, today):
        return ""

    matches = {m.incident.pst_no: m for m in map_incidents(pending, mappings)}
    gaps = [i for i in pending if matches[i.pst_no].is_gap]
    reason = (
        f"{len(pending)}건 쌓임"
        if len(pending) >= THRESHOLD
        else f"{(today - since).days}일 경과"
    )

    lines = [
        f"{MENTION} {since} 이후 **{len(pending)}건**이 수집됐습니다. ({reason})",
        "",
        f"- 조문을 받은 사고: **{len(pending) - len(gaps)}건**",
        f"- 아직 못 받은 사고: **{len(gaps)}건**"
        + ("" if not gaps else " — 별도 이슈로도 올라갑니다"),
        "",
        "| 발생 | 지역 | 업종 | 사고 | 적용 |",
        "|---|---|---|---|---|",
    ]
    for inc in pending[:TABLE_LIMIT]:
        match = matches[inc.pst_no]
        when = inc.occurred_at.date().isoformat() if inc.occurred_at else "-"
        site = inc.site_type.value if inc.site_type else "-"
        applied = "**없음**" if match.is_gap else match.results[0].mapping.work_type.name_ko
        lines.append(
            f"| {when} | {inc.region or '-'} | {site} | "
            f"[{_link_label(inc.title)}]({inc.source_url}) | {applied} |"
        )
    if len(pending) > TABLE_LIMIT:
        lines.append(f"| … | | | 외 {len(pending) - TABLE_LIMIT}건 | |")

    lines += [
        "",
        "---",
        "",
        "`scripts/report_new_incidents.py` 자동 생성. "
        f"보내는 기준은 **{THRESHOLD}건 또는 {MAX_AGE_DAYS}일 중 먼저**입니다 — "
        "근거는 `scripts/simulate_alert_policies.py`.",
        "",
        "⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다. "
        "개별 사고의 법령 위반 여부를 뜻하지 않습니다.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="쌓인 신규 사고 요약 (보낼 때가 아니면 빈 출력)")
    ap.add_argument("--since", type=datetime.date.fromisoformat, required=True)
    ap.add_argument("--today", type=datetime.date.fromisoformat, default=datetime.date.today())
    args = ap.parse_args()

    dataset = load_dataset()
    incidents = load_incidents()
    body = render(
        pending_since(incidents, args.since),
        list(dataset.mappings.values()),
        args.since,
        args.today,
    )
    if body:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
