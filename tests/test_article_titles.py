import json
import re

import pytest
import yaml

from .conftest import DATA_DIR, FIXTURES

# 제목표는 law.go.kr 원문에서 뜬 스냅샷이다. 파일명의 날짜가 그 시점이고,
# 법이 바뀌면 사람이 다시 떠야 한다 — 이 테스트는 그 사실을 알지 못한다.
TITLES = FIXTURES / "osh-rule-titles-2026-10-14.json"
LAW_ID = "osh-rule"


def normalize(title: str) -> str:
    """구분자와 공백만 맞춘다.

    법령은 가운뎃점으로 `ㆍ`(U+318D HANGUL LETTER ARAEA)를 쓰고 이 저장소는
    `·`(U+00B7 MIDDLE DOT)로 적는다. 둘 다 읽는 사람에게는 같은 글자다.

    `unicodedata.normalize("NFKC", ...)` 를 먼저 돌리면 안 된다. U+318D 는
    호환 자모라 NFKC 가 다른 코드포인트로 분해해 버리고, 그 뒤에 치환하면
    아무것도 걸리지 않는다. 멀쩡한 제목 16건이 불일치로 나와서 알았다.
    """
    for dot in "ㆍ‧・":
        title = title.replace(dot, "·")
    return re.sub(r"\s+", "", title)


@pytest.fixture(scope="module")
def law_titles() -> dict[str, str]:
    return json.loads(TITLES.read_text(encoding="utf-8"))


def _recorded():
    for path in sorted((DATA_DIR / "mappings").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for law in data["applicable_laws"]:
            if law["law_id"] != LAW_ID:
                continue
            for article in law["articles"]:
                yield path.name, article["article_ref"], article["article_title"]


def test_every_article_title_matches_the_law(law_titles):
    wrong = [
        (name, ref, got, law_titles.get(ref))
        for name, ref, got in _recorded()
        if ref in law_titles and normalize(got) != normalize(law_titles[ref])
    ]
    assert wrong == [], wrong


def test_every_article_exists_in_the_law(law_titles):
    """데이터셋이 없는 조문을 가리키면 오타이거나 스냅샷이 낡은 것이다."""
    missing = [(name, ref) for name, ref, _ in _recorded() if ref not in law_titles]
    assert missing == [], missing


def test_normalize_only_touches_separators_and_spaces():
    assert normalize("원동기ㆍ회전축 등의 위험 방지") == normalize("원동기·회전축 등의 위험 방지")
    assert normalize("비계의 재료") != normalize("비계의 점검 및 보수")
