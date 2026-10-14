import importlib.util
import json

import pytest

from .conftest import REPO_ROOT


@pytest.fixture(scope="module")
def builder():
    path = REPO_ROOT / "scripts" / "build_law_coverage_report.py"
    spec = importlib.util.spec_from_file_location("build_law_coverage_report", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_structure_snapshot_is_not_truncated(builder):
    """좌측 목차는 절 이름을 '...' 로 자른다. 그걸 뜨면 리포트가 못 쓰게 된다."""
    sections = json.loads(builder.STRUCTURE.read_text(encoding="utf-8"))
    assert sections
    for s in sections:
        label = s["part"] + s["chapter"] + s["section"]
        assert "..." not in label, s


def test_every_article_appears_once(builder):
    sections = json.loads(builder.STRUCTURE.read_text(encoding="utf-8"))
    refs = [a for s in sections for a in s["articles"]]
    assert len(refs) == len(set(refs))


def test_covered_articles_are_all_in_the_snapshot(builder):
    """데이터셋이 스냅샷에 없는 조문을 참조하면 스냅샷이 낡았다는 뜻이다."""
    sections = json.loads(builder.STRUCTURE.read_text(encoding="utf-8"))
    known = {a for s in sections for a in s["articles"]}
    used = set(builder.covered_articles(REPO_ROOT / "data" / "mappings"))
    assert used <= known, sorted(used - known)


def test_report_is_up_to_date(builder):
    """매핑을 추가하고 리포트를 다시 만들지 않으면 여기서 걸린다."""
    sections = json.loads(builder.STRUCTURE.read_text(encoding="utf-8"))
    by_article = builder.covered_articles(REPO_ROOT / "data" / "mappings")
    expected = builder.render(sections, by_article)
    actual = builder.OUT.read_text(encoding="utf-8")
    assert actual == expected, "python scripts/build_law_coverage_report.py 를 다시 실행하세요"
