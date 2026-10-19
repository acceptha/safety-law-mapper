#!/usr/bin/env python
"""알림 정책을 수집분 전체에 소급 적용해 발송 횟수·지연·유효비율을 잰다.

Usage: python scripts/simulate_alert_policies.py

"몇 건 쌓였을 때 보내야 하나"는 취향이 아니라 계산이다. 수집기는 매일 07:00
KST 에 돌므로 게시 다음 날 아침에 손에 들어온다고 보고, 각 정책이 그 흐름에
어떻게 반응했을지를 세 가지로 센다.

- **빈도** 주당 몇 번 울리나. 많으면 읽지 않게 된다
- **최악 지연** 게시 후 며칠 만에 알리나. 길면 알림이 늦어 쓸모가 준다
- **유효** 그 알림에 손이 필요한 것(미매핑)이 하나라도 들었나

유효 비율은 공백 알림(`report_new_gaps.py`)과 비교하기 위한 것이지, 요약
알림이 올려야 할 값은 아니다. 요약은 '무슨 일이 있었나'를 전하는 쪽이고
손이 필요한 날은 공백 알림이 따로 맡는다.

미매핑 여부는 **현재 매핑**으로 판정한다. 과거를 재현하려는 게 아니라
"지금 커버리지에서 앞으로 얼마나 울릴 것인가"를 묻는 것이기 때문이다.
"""

from __future__ import annotations

import datetime
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from safety_law_mapper.incidents import Incident, load_incidents, map_incidents  # noqa: E402
from safety_law_mapper.loader import load_dataset  # noqa: E402


def simulate(
    arrivals: dict[datetime.date, list[Incident]],
    calendar: list[datetime.date],
    gap_ids: set[str],
    decide,
) -> list[dict]:
    """정책 하나를 돌려 발송 기록을 낸다.

    decide(pending, today, days_held) -> bool
    """
    pending: list[Incident] = []
    held_since: datetime.date | None = None
    sends: list[dict] = []
    for today in calendar:
        arrived = arrivals.get(today, [])
        if arrived and held_since is None:
            held_since = today
        pending += arrived
        if not pending:
            continue
        if decide(pending, today, (today - held_since).days):
            delays = [(today - i.posted_at).days for i in pending]
            sends.append(
                {
                    "n": len(pending),
                    "gaps": sum(1 for i in pending if i.pst_no in gap_ids),
                    "worst": max(delays),
                    "median": statistics.median(delays),
                }
            )
            pending, held_since = [], None
    return sends


def describe(label: str, sends: list[dict], weeks: float) -> str:
    if not sends:
        return f"{label:26s}  (발송 없음)"
    return (
        f"{label:26s} {len(sends):4d}회  {len(sends) / weeks:4.2f}/주  "
        f"평균 {statistics.mean(s['n'] for s in sends):5.1f}건  "
        f"지연 중앙 {statistics.median(s['median'] for s in sends):3.0f}일 "
        f"최악 {max(s['worst'] for s in sends):3d}일  "
        f"유효 {sum(1 for s in sends if s['gaps']) / len(sends) * 100:3.0f}%"
    )


def main() -> int:
    dataset = load_dataset()
    incidents = load_incidents()
    gap_ids = {
        m.incident.pst_no
        for m in map_incidents(incidents, list(dataset.mappings.values()))
        if m.is_gap
    }

    by_day: dict[datetime.date, list[Incident]] = defaultdict(list)
    for incident in incidents:
        by_day[incident.posted_at].append(incident)
    days = sorted(by_day)
    span = (days[-1] - days[0]).days + 1
    weeks = span / 7

    # 게시 다음 날 아침에 수집된다.
    arrivals = {d + datetime.timedelta(days=1): v for d, v in by_day.items()}
    calendar = [days[0] + datetime.timedelta(days=k) for k in range(span + 2)]

    print(f"기간 {days[0]} ~ {days[-1]} ({span}일 = {weeks:.1f}주)")
    print(f"사고 {len(incidents)}건 / 미매핑 {len(gap_ids)}건")
    sizes = Counter(len(v) for v in by_day.values())
    print(
        f"게시가 있던 날 {len(days)}일 (하루 중앙값 "
        f"{statistics.median(len(v) for v in by_day.values()):.0f}건, 최대 {max(sizes)}건), "
        f"게시 간격 중앙값 "
        f"{statistics.median((days[k + 1] - days[k]).days for k in range(len(days) - 1)):.0f}일"
    )
    print()

    rows = [("수집될 때마다", lambda p, t, h: True)]
    rows += [(f"{n}건 쌓이면", lambda p, t, h, n=n: len(p) >= n) for n in (3, 5, 8, 10, 15, 20)]
    rows += [
        (f"{n}건 또는 {d}일", lambda p, t, h, n=n, d=d: len(p) >= n or h >= d)
        for n, d in ((5, 7), (8, 7), (10, 7), (8, 14), (10, 14))
    ]
    rows += [
        ("매주 월요일", lambda p, t, h: t.weekday() == 0),
        ("격주 월요일", lambda p, t, h: t.weekday() == 0 and t.isocalendar()[1] % 2 == 0),
        ("매월 1일", lambda p, t, h: t.day == 1),
    ]

    for label, decide in rows:
        print(describe(label, simulate(arrivals, calendar, gap_ids, decide), weeks))

    # 공백만 보는 쪽은 묶지 않는다 — 생기는 날 바로 울린다.
    gap_days = {d: [i for i in v if i.pst_no in gap_ids] for d, v in arrivals.items()}
    gap_days = {d: v for d, v in gap_days.items() if v}
    print()
    print(
        f"{'공백 생기면 즉시':26s} {len(gap_days):4d}회  {len(gap_days) / weeks:4.2f}/주  "
        f"평균 {statistics.mean(len(v) for v in gap_days.values()):5.1f}건  "
        f"지연 중앙   1일 최악   1일  유효 100%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
