import datetime
import json

import pytest

from safety_law_mapper.incidents import (
    AccidentType,
    Incident,
    build_incident,
    coverage,
    extract_keywords,
    load_incidents,
    load_lexicon,
    map_incident,
    map_incidents,
    parse_occurred_at,
    parse_region,
    strip_html,
    write_incidents,
)

from .conftest import DATA_DIR, FIXTURES

FETCHED = datetime.date(2026, 8, 28)


@pytest.fixture(scope="module")
def posts():
    return json.loads((FIXTURES / "incident_posts.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lexicon():
    return load_lexicon(DATA_DIR / "incidents" / "lexicon.yaml")


@pytest.fixture(scope="module")
def mapping_keywords(dataset):
    return {k for m in dataset.mappings.values() for k in m.work_type.keywords}


def _build(post, lexicon, mapping_keywords, **kw):
    return build_incident(
        pst_no=post["pstNo"],
        title=post["pstNm"],
        body=post["pstCn"],
        posted_at=datetime.datetime.strptime(post["regYmd"], "%Y%m%d").date(),
        fetched_at=FETCHED,
        lexicon=lexicon,
        mapping_keywords=mapping_keywords,
        **kw,
    )


def test_strip_html_collapses_per_character_markup():
    html = "<p>2026. 8. 19 <span>(</span><span>수</span><span>)</span></p><p>떨어짐</p>"
    assert strip_html(html) == "2026. 8. 19 (수)\n떨어짐"


def test_parse_region_handles_comma_and_bare_forms():
    assert parse_region("[8/19, 부산 강서구] 이동식 비계가 넘어져 떨어짐") == "부산 강서구"
    assert parse_region("[8/23 경기 파주시] 철근 다발이 떨어져 깔림") == "경기 파주시"
    assert parse_region("제목만 있고 대괄호가 없음") is None


def test_parse_occurred_at_reads_date_and_time():
    body = "2026. 8. 19 (수), 14:08경\n부산 강서구 소재 공사현장에서"
    assert parse_occurred_at(body, datetime.date(2026, 8, 27)) == datetime.datetime(
        2026, 8, 19, 14, 8
    )


def test_parse_occurred_at_rejects_future_misread():
    body = "2099. 1. 1 발생"
    assert parse_occurred_at(body, datetime.date(2026, 8, 27)) is None


def test_build_incident_extracts_structured_facts(posts, lexicon, mapping_keywords):
    inc = _build(posts[0], lexicon, mapping_keywords)
    assert inc.region == "부산 강서구"
    assert inc.site_type == "공사현장"
    assert inc.fatalities == 1
    assert inc.fall_height_m == 1.8
    assert AccidentType.FALL in inc.accident_type
    assert "비계" in inc.work_keywords
    assert inc.source_url.endswith(inc.pst_no)


def test_stopwords_do_not_become_signals(posts, lexicon, mapping_keywords):
    """'해체'/'작업' 같은 범용어는 단독 신호가 되면 안 된다 (기획서 §4.3)."""
    roof = _build(posts[2], lexicon, mapping_keywords)
    assert "해체" not in roof.work_keywords
    assert "작업" not in roof.work_keywords


def test_extract_keywords_maps_surface_variants(lexicon, mapping_keywords):
    # 원문은 띄어 쓰지만 매핑 키워드는 '연삭숫돌' — 렉시콘이 이어줘야 한다.
    kws = extract_keywords("깨진 연삭 숫돌 파편에 맞음", lexicon, mapping_keywords)
    assert "연삭기" in kws


def test_compound_word_does_not_leak_a_keyword(lexicon, mapping_keywords):
    """'가용접된 러그' 때문에 인양 사고가 용접으로 매칭되면 안 된다."""
    text = "호이스트로 철판을 인양하던 중 철판에 가용접된 인양용 러그가 파단되면서"
    assert "용접" not in extract_keywords(text, lexicon, mapping_keywords)
    assert "인양" in extract_keywords(text, lexicon, mapping_keywords)


def test_suppression_keeps_a_genuine_mention(lexicon, mapping_keywords):
    """합성어가 있어도 진짜 용접 작업이 함께 언급되면 신호를 유지해야 한다."""
    text = "용접 작업 중 가용접된 브래킷이 떨어져"
    assert "용접" in extract_keywords(text, lexicon, mapping_keywords)


def test_roof_incident_maps_to_roof_work(posts, lexicon, mapping_keywords, dataset):
    inc = _build(posts[2], lexicon, mapping_keywords)
    m = map_incident(inc, list(dataset.mappings.values()))
    assert not m.is_gap
    assert m.results[0].mapping.mapping_id == "roof-work"


def test_septic_tank_incident_maps_to_confined_space(
    posts, lexicon, mapping_keywords, dataset
):
    inc = _build(posts[3], lexicon, mapping_keywords)
    m = map_incident(inc, list(dataset.mappings.values()))
    assert "confined-space-work" in [r.mapping.mapping_id for r in m.results]


def test_unknown_work_type_is_reported_as_gap(posts, lexicon, mapping_keywords, dataset):
    """둥근톱 매핑은 아직 없다 — 조용히 오답을 내지 말고 공백으로 남겨야 한다."""
    inc = _build(posts[4], lexicon, mapping_keywords)
    m = map_incident(inc, list(dataset.mappings.values()))
    assert m.is_gap


def test_incident_without_keywords_never_guesses(dataset):
    inc = Incident(
        pst_no="X",
        posted_at=datetime.date(2026, 1, 1),
        source_url="https://portal.kosha.or.kr/x",
        fetched_at=FETCHED,
    )
    assert map_incident(inc, list(dataset.mappings.values())).is_gap


def test_store_title_can_be_omitted(posts, lexicon, mapping_keywords):
    inc = _build(posts[0], lexicon, mapping_keywords, store_title=False)
    assert inc.title is None
    # 제목을 빼도 매핑 신호는 유지된다.
    assert inc.work_keywords


def test_jsonl_roundtrip_is_lossless(tmp_path, posts, lexicon, mapping_keywords):
    built = [_build(p, lexicon, mapping_keywords) for p in posts]
    path = tmp_path / "alerts.jsonl"
    write_incidents(built, path)
    loaded = load_incidents(path)
    assert {i.pst_no for i in loaded} == {i.pst_no for i in built}
    assert loaded == sorted(loaded, key=lambda i: (i.posted_at, i.pst_no), reverse=True)


def test_load_incidents_missing_file_is_empty(tmp_path):
    assert load_incidents(tmp_path / "nope.jsonl") == []


def test_coverage_counts_mapped_and_total(posts, lexicon, mapping_keywords, dataset):
    built = [_build(p, lexicon, mapping_keywords) for p in posts]
    matches = map_incidents(built, list(dataset.mappings.values()))
    mapped, total = coverage(matches)
    assert total == len(posts)
    assert 0 < mapped < total  # 둥근톱 1건은 공백으로 남아야 한다
