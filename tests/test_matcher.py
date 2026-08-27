from safety_law_mapper.matcher import Query, match
from safety_law_mapper.models import WorkCategory


def _mappings(dataset):
    return list(dataset.mappings.values())


def test_empty_query_matches_nothing(dataset):
    assert match(_mappings(dataset), Query()) == []


def test_keyword_match(dataset):
    results = match(_mappings(dataset), Query(keywords=["밀폐공간"]))
    ids = [r.mapping.mapping_id for r in results]
    assert "confined-space-work" in ids


def test_composite_query_ranks_composite_first(dataset):
    results = match(_mappings(dataset), Query(keywords=["밀폐공간", "용접"]))
    assert results[0].mapping.mapping_id == "confined-space-welding"


def test_category_match(dataset):
    results = match(_mappings(dataset), Query(category=WorkCategory.CONFINED_SPACE))
    ids = {r.mapping.mapping_id for r in results}
    assert ids == {"confined-space-work", "confined-space-welding"}


def test_category_beats_keyword_count(dataset):
    # welding-cutting gets keyword hits; confined-space entries get category match
    results = match(
        _mappings(dataset),
        Query(keywords=["용접"], category=WorkCategory.CONFINED_SPACE),
    )
    assert results[0].category_match is True


def test_equipment_condition_excludes_on_mismatch(dataset):
    # welding-cutting requires welding-machine; a disjoint equipment list excludes it
    results = match(_mappings(dataset), Query(keywords=["용접"], equipment=["forklift"]))
    ids = [r.mapping.mapping_id for r in results]
    assert "welding-cutting" not in ids


def test_absent_query_fields_do_not_exclude(dataset):
    # No equipment given in query -> equipment-conditioned entries still match
    results = match(_mappings(dataset), Query(keywords=["용접"]))
    ids = [r.mapping.mapping_id for r in results]
    assert "welding-cutting" in ids


def test_deterministic_order(dataset):
    q = Query(keywords=["밀폐공간", "용접"])
    r1 = [r.mapping.mapping_id for r in match(_mappings(dataset), q)]
    r2 = [r.mapping.mapping_id for r in match(_mappings(dataset), q)]
    assert r1 == r2


def test_exact_keyword_beats_substring(dataset):
    # '타워크레인' exactly matches tower-crane-assembly's keyword;
    # crane-lifting matches only via '크레인' containment
    results = match(_mappings(dataset), Query(keywords=["타워크레인"]))
    ids = [r.mapping.mapping_id for r in results]
    assert ids.index("tower-crane-assembly") < ids.index("crane-lifting")


def test_exact_keyword_beats_substring_gas_welding(dataset):
    # '가스용접' is an exact keyword of gas-welding; other welding mappings
    # match only via '용접' containment
    results = match(_mappings(dataset), Query(keywords=["가스용접"]))
    assert results[0].mapping.mapping_id == "gas-welding"
