import importlib.util
import json

import pytest

from .conftest import DATA_DIR, FIXTURES, REPO_ROOT

# 날짜표는 law.go.kr 원문에서 뜬 스냅샷이다. 파일명의 날짜가 그 시점이고,
# 법이 바뀌면 사람이 다시 떠야 한다 — 이 테스트는 그 사실을 알지 못한다.
AMENDMENTS = FIXTURES / "osh-rule-amendments-2026-10-14.json"


@pytest.fixture(scope="module")
def checker():
    path = REPO_ROOT / "scripts" / "check_article_dates.py"
    spec = importlib.util.spec_from_file_location("check_article_dates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flags_an_article_amended_after_the_recorded_date(checker):
    rows = checker.stale_entries(DATA_DIR / "mappings", {"제42조": "2099-01-01"})
    assert rows, "기록 이후 개정된 조문을 잡지 못했습니다"
    assert {r[1] for r in rows} == {"제42조"}


def test_a_later_enforcement_date_is_not_an_alarm(checker):
    """valid_from 은 시행일이라 공포일보다 늦다. 그 차이를 경보로 내면 안 된다.

    제179조가 실제 사례다 — 2019. 12. 26. 공포, 2021. 1. 16. 시행.
    """
    rows = checker.stale_entries(DATA_DIR / "mappings", {"제179조": "2019-12-26"})
    assert rows == []


def test_unknown_article_is_skipped(checker):
    assert checker.stale_entries(DATA_DIR / "mappings", {"제99999조": "2099-01-01"}) == []


def test_seed_data_has_no_article_older_than_its_last_amendment(checker):
    """감사 결과를 고정한다."""
    latest = json.loads(AMENDMENTS.read_text(encoding="utf-8"))
    rows = checker.stale_entries(DATA_DIR / "mappings", latest)
    assert rows == [], rows
