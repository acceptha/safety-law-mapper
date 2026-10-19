"""`scripts/report_new_gaps.py` — 알림의 신호가 '새 사고'가 아니라 '새 공백'인지.

사고는 주 2~3건씩 들어오고 대부분은 이미 맞는 조문으로 간다. 들어올 때마다
알리면 두 주 만에 아무도 보지 않게 되고, 그러면 정작 손이 필요한 날의 알림도
같이 묻힌다. 그래서 여기서 지키는 성질은 두 가지다 — 매핑된 사고로는 울리지
않을 것, 공백이 없으면 **아무것도 출력하지 않을 것**(호출부가 빈 출력을 보고
이슈를 만들지 않는다).
"""

import datetime
import importlib.util

from safety_law_mapper.incidents import Incident, SiteType

from .conftest import REPO_ROOT

COLLECTED = datetime.date(2026, 8, 28)


def _load_reporter():
    """스크립트는 scripts/ 아래라 패키지가 아니다. 파일에서 직접 읽는다."""
    path = REPO_ROOT / "scripts" / "report_new_gaps.py"
    spec = importlib.util.spec_from_file_location("report_new_gaps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _incident(pst_no: str, keywords: list[str], fetched_at: datetime.date) -> Incident:
    return Incident(
        pst_no=pst_no,
        posted_at=datetime.date(2026, 8, 27),
        occurred_at=datetime.datetime(2026, 8, 19, 14, 8),
        region="부산 강서구",
        site_type=SiteType.CONSTRUCTION,
        accident_type=[],
        fatalities=1,
        work_keywords=keywords,
        source_url="https://portal.kosha.or.kr/test",
        fetched_at=fetched_at,
        title="[8/19, 부산 강서구] 이동식 비계가 넘어져 떨어짐",
    )


def test_a_mapped_incident_does_not_raise_a_gap(dataset):
    """오늘 들어온 사고라도 조문을 받았으면 알릴 일이 아니다."""
    reporter = _load_reporter()
    mappings = list(dataset.mappings.values())
    incidents = [_incident("MAPPED00000000000001", ["이동식비계"], COLLECTED)]

    assert reporter.new_gaps(incidents, mappings, COLLECTED) == []


def test_only_todays_gaps_are_reported(dataset):
    """어제의 공백까지 매일 다시 알리면 같은 알림이 반복된다."""
    reporter = _load_reporter()
    mappings = list(dataset.mappings.values())
    incidents = [
        _incident("TODAYGAP000000000001", [], COLLECTED),
        _incident("OLDGAP0000000000001X", [], COLLECTED - datetime.timedelta(days=1)),
    ]

    gaps = reporter.new_gaps(incidents, mappings, COLLECTED)
    assert [g.pst_no for g in gaps] == ["TODAYGAP000000000001"]


def test_no_gaps_renders_nothing(dataset):
    """빈 출력이 '알릴 것 없음'의 신호다. 머리글만 찍어도 이슈가 열린다."""
    reporter = _load_reporter()
    assert reporter.render([], reporter.empty_sections(list(dataset.mappings.values()))) == ""


def test_rendered_body_links_the_source_and_carries_the_disclaimer(dataset):
    reporter = _load_reporter()
    gap = _incident("TODAYGAP000000000001", [], COLLECTED)

    body = reporter.render([gap], [])

    assert "https://portal.kosha.or.kr/test" in body
    # 제목 앞의 "[8/19, 부산 강서구]"가 링크 라벨에 남으면 마크다운이 첫 ']'에서
    # 링크 텍스트를 끊어 링크가 깨진다.
    assert "[이동식 비계가 넘어져 떨어짐](" in body
    assert "법적 판단을 대체하지 않습니다" in body
