import yaml

from safety_law_mapper.matcher import Query, match
from safety_law_mapper.models import WorkCategory

from .conftest import FIXTURES


def _load_cases():
    return yaml.safe_load((FIXTURES / "golden_queries.yaml").read_text(encoding="utf-8"))


def test_golden_queries(dataset):
    cases = _load_cases()
    assert cases, "golden fixture file is empty"
    for case in cases:
        q = case["query"]
        query = Query(
            keywords=q.get("keywords", []),
            category=WorkCategory(q["category"]) if q.get("category") else None,
            employees=q.get("employees"),
        )
        results = match(list(dataset.mappings.values()), query)
        got_ids = [r.mapping.mapping_id for r in results]

        for mid in case.get("must_include_mappings", []):
            assert mid in got_ids, f"[{case['name']}] missing mapping: {mid}"

        top = case.get("top_mapping")
        if top:
            assert got_ids and got_ids[0] == top, (
                f"[{case['name']}] expected top {top}, got {got_ids[:3]}"
            )

        for req in case.get("must_include_articles", []):
            mapping = dataset.mappings[req["mapping_id"]]
            refs = {
                (al.law_id, art.article_ref)
                for al in mapping.applicable_laws
                for art in al.articles
            }
            assert (req["law_id"], req["article_ref"]) in refs, (
                f"[{case['name']}] {req['mapping_id']} must include "
                f"{req['law_id']} {req['article_ref']}"
            )
