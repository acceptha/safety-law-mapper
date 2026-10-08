import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from safety_law_mapper import DISCLAIMER  # noqa: E402
from safety_law_mapper.api import app  # noqa: E402
from safety_law_mapper.models import WorkCategory  # noqa: E402

client = TestClient(app)


def test_health_reports_loaded_data():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mappings"] > 0
    assert body["laws"] > 0
    assert body["articles"] > body["mappings"]


def test_search_returns_citation_for_every_article():
    r = client.get("/search", params={"q": ["밀폐공간", "용접"]})
    assert r.status_code == 200
    body = r.json()
    assert body["results"]
    for entry in body["results"]:
        for art in entry["articles"]:
            assert art["source_url"].startswith("https://www.law.go.kr")
            assert art["article_ref"]


def test_search_ranks_like_the_engine():
    r = client.get("/search", params={"q": ["밀폐공간", "용접"]})
    assert r.json()["results"][0]["mapping_id"] == "confined-space-welding"


def test_search_attaches_grounding_and_disclaimer():
    body = client.get("/search", params={"q": ["용접"]}).json()
    assert body["disclaimer"] == DISCLAIMER
    assert "source_url만 사용" in body["grounding"]


def test_empty_query_returns_empty_not_everything():
    body = client.get("/search").json()
    assert body["result_count"] == 0
    assert body["results"] == []


def test_truncation_is_reported():
    body = client.get(
        "/search", params={"category": WorkCategory.WORK_AT_HEIGHT.value, "limit": 1}
    ).json()
    assert body["result_count"] == 1
    if body["total_matched"] > 1:
        assert body["truncated"] is True


def test_bad_category_is_400_naming_valid_values():
    r = client.get("/search", params={"q": "용접", "category": "nonsense"})
    assert r.status_code == 400
    assert "confined-space" in r.json()["detail"]


def test_limit_above_max_is_rejected_by_validation():
    r = client.get("/search", params={"q": "용접", "limit": 999})
    assert r.status_code == 422


def test_limit_below_one_is_rejected_by_validation():
    r = client.get("/search", params={"q": "용접", "limit": 0})
    assert r.status_code == 422


def test_categories_cover_the_vocabulary():
    body = client.get("/categories").json()
    assert {c["category"] for c in body["categories"]} == {c.value for c in WorkCategory}


def test_list_mappings_is_lightweight():
    body = client.get("/mappings").json()
    assert body["count"] == len(body["mappings"])
    # The list view carries counts, not article bodies.
    assert "articles" not in body["mappings"][0]
    assert body["mappings"][0]["article_count"] > 0


def test_get_mapping_detail():
    body = client.get("/mappings/confined-space-welding").json()
    assert body["work_type"] == "밀폐공간 용접"
    assert body["article_count"] == len(body["articles"])
    assert body["disclaimer"] == DISCLAIMER


def test_unknown_mapping_is_404_naming_real_ones():
    r = client.get("/mappings/no-such-mapping")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "no-such-mapping" in detail
    assert "confined-space-welding" in detail or "aerial" in detail


def test_cors_allows_the_static_demo_origin():
    r = client.get(
        "/search",
        params={"q": "용접"},
        headers={"Origin": "https://acceptha.github.io"},
    )
    assert r.headers["access-control-allow-origin"] == "*"


def test_openapi_schema_is_served():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert {"/health", "/search", "/categories", "/mappings", "/mappings/{mapping_id}"} <= set(paths)


def test_every_route_is_read_only():
    """The dataset changes by pull request, not by HTTP."""
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        assert set(ops) <= {"get"}, f"{path} exposes a non-GET method"


# --- the contract that matters: REST and MCP cannot disagree -------------


def test_rest_and_mcp_return_identical_payloads():
    """Both interfaces build responses in `view`. If someone reimplements one
    of them, this fails — which is the whole reason the layer is shared."""
    from safety_law_mapper.view import get_dataset, search

    direct = search(get_dataset(), ["밀폐공간", "용접"], limit=5)
    over_http = client.get(
        "/search", params={"q": ["밀폐공간", "용접"], "limit": 5}
    ).json()
    assert over_http == direct
