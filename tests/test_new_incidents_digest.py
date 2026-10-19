"""`scripts/report_new_incidents.py` — 묶음 알림의 발송 조건.

지키는 성질은 네 가지다.

1. 덜 쌓이고 덜 지났으면 **보내지 않는다** (빈 출력이 '보내지 않음'의 신호)
2. 임계값만큼 쌓이면 보낸다
3. 덜 쌓여도 상한 일수가 지나면 보낸다 — **순수 개수 임계값은 조용한 달에
   20일을 묵힌다**(`simulate_alert_policies.py`). 상한이 그걸 막는다
4. 보낼 게 없으면 날짜가 아무리 지나도 보내지 않는다
"""

import datetime
import importlib.util

from safety_law_mapper.incidents import Incident, SiteType

from .conftest import REPO_ROOT

SINCE = datetime.date(2026, 8, 20)


def _load_digest():
    path = REPO_ROOT / "scripts" / "report_new_incidents.py"
    spec = importlib.util.spec_from_file_location("report_new_incidents", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _incident(n: int, fetched_at: datetime.date, keywords: list[str] | None = None) -> Incident:
    return Incident(
        pst_no=f"TESTDIGEST{n:010d}",
        posted_at=fetched_at - datetime.timedelta(days=1),
        occurred_at=datetime.datetime(2026, 8, 19, 14, 8),
        region="부산 강서구",
        site_type=SiteType.CONSTRUCTION,
        accident_type=[],
        fatalities=1,
        work_keywords=keywords if keywords is not None else ["이동식비계"],
        source_url="https://portal.kosha.or.kr/test",
        fetched_at=fetched_at,
        title="[8/19, 부산 강서구] 이동식 비계가 넘어져 떨어짐",
    )


def test_holds_until_the_batch_is_worth_sending(dataset):
    digest = _load_digest()
    collected = SINCE + datetime.timedelta(days=1)
    pending = [_incident(n, collected) for n in range(digest.THRESHOLD - 1)]

    body = digest.render(pending, list(dataset.mappings.values()), SINCE, collected)

    assert body == ""


def test_sends_once_the_threshold_is_reached(dataset):
    digest = _load_digest()
    collected = SINCE + datetime.timedelta(days=1)
    pending = [_incident(n, collected) for n in range(digest.THRESHOLD)]

    body = digest.render(pending, list(dataset.mappings.values()), SINCE, collected)

    assert f"**{digest.THRESHOLD}건**" in body
    assert "건 쌓임" in body


def test_sends_a_small_batch_once_it_has_waited_long_enough(dataset):
    """순수 개수 임계값이면 조용한 달에 20일을 묵는다. 상한이 그걸 막는다."""
    digest = _load_digest()
    collected = SINCE + datetime.timedelta(days=1)
    late = SINCE + datetime.timedelta(days=digest.MAX_AGE_DAYS)
    pending = [_incident(0, collected)]

    assert digest.render(pending, list(dataset.mappings.values()), SINCE, collected) == ""
    body = digest.render(pending, list(dataset.mappings.values()), SINCE, late)
    assert f"{digest.MAX_AGE_DAYS}일 경과" in body


def test_silence_when_nothing_arrived(dataset):
    """오래 지났다는 이유만으로 빈 알림을 보내면 안 된다."""
    digest = _load_digest()
    long_after = SINCE + datetime.timedelta(days=digest.MAX_AGE_DAYS * 5)

    assert digest.render([], list(dataset.mappings.values()), SINCE, long_after) == ""


def test_body_mentions_the_owner_and_separates_mapped_from_gaps(dataset):
    """봇이 만든 이슈는 멘션이 없으면 소유자에게 알림이 가지 않는다."""
    digest = _load_digest()
    collected = SINCE + datetime.timedelta(days=1)
    pending = [_incident(n, collected) for n in range(digest.THRESHOLD - 1)]
    pending.append(_incident(99, collected, keywords=[]))  # 매핑 못 받는 사고

    body = digest.render(pending, list(dataset.mappings.values()), SINCE, collected)

    assert body.startswith(digest.MENTION)
    assert "아직 못 받은 사고: **1건**" in body
    assert "**없음**" in body


def test_only_counts_what_arrived_after_the_last_send(dataset):
    digest = _load_digest()
    older = _incident(1, SINCE)  # 경계일 = 이미 보낸 묶음
    newer = _incident(2, SINCE + datetime.timedelta(days=1))

    assert [i.pst_no for i in digest.pending_since([older, newer], SINCE)] == [newer.pst_no]


def test_simulation_shows_why_a_day_cap_is_needed():
    """정책 상수의 근거가 되는 시뮬레이터 자체를 고정한다.

    게시가 드문드문한 구간을 만들어, 순수 개수 임계값이 묶음을 더 오래
    묵히고 일수 상한이 그걸 끊는지 본다. 이게 뒤집히면 상수를 다시 재야 한다.
    """
    import importlib.util

    path = REPO_ROOT / "scripts" / "simulate_alert_policies.py"
    spec = importlib.util.spec_from_file_location("simulate_alert_policies", path)
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)

    start = datetime.date(2026, 1, 1)
    # 열흘에 한 건씩만 올라오는 조용한 구간.
    arrivals = {
        start + datetime.timedelta(days=10 * n): [_incident(n, start)] for n in range(6)
    }
    calendar = [start + datetime.timedelta(days=k) for k in range(70)]

    count_only = sim.simulate(arrivals, calendar, set(), lambda p, t, h: len(p) >= 8)
    hybrid = sim.simulate(arrivals, calendar, set(), lambda p, t, h: len(p) >= 8 or h >= 7)

    assert count_only == []  # 8건이 끝내 차지 않아 한 번도 울리지 않는다
    assert len(hybrid) == 6  # 상한이 걸려 건건이 나간다
