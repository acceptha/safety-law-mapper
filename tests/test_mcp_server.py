import pytest

from safety_law_mapper import DISCLAIMER
from safety_law_mapper.mcp_server import (
    GROUNDING_RULE,
    MAX_LIMIT,
    UNVERIFIED,
    build_server,
    categories,
    clamp_limit,
    format_mapping,
    search,
)
from safety_law_mapper.models import WorkCategory


def test_search_returns_citation_for_every_article(dataset):
    """The whole point: nothing comes back without a traceable source."""
    payload = search(dataset, keywords=["밀폐공간", "용접"])
    assert payload["results"]
    for entry in payload["results"]:
        assert entry["articles"]
        for art in entry["articles"]:
            assert art["source_url"].startswith("https://www.law.go.kr")
            assert art["article_ref"]


def test_search_ranks_like_the_cli(dataset):
    # Same engine, so the composite mapping wins here exactly as in test_matcher.
    payload = search(dataset, keywords=["밀폐공간", "용접"])
    assert payload["results"][0]["mapping_id"] == "confined-space-welding"


def test_grounding_rule_and_disclaimer_are_always_attached(dataset):
    payload = search(dataset, keywords=["용접"])
    assert payload["grounding"] == GROUNDING_RULE
    assert payload["disclaimer"] == DISCLAIMER


def test_empty_query_returns_nothing(dataset):
    payload = search(dataset)
    assert payload["result_count"] == 0
    assert payload["results"] == []
    assert payload["total_matched"] == 0


def test_limit_caps_results_and_reports_truncation(dataset):
    payload = search(dataset, category=WorkCategory.WORK_AT_HEIGHT.value, limit=1)
    assert payload["result_count"] == 1
    if payload["total_matched"] > 1:
        assert payload["truncated"] is True


def test_limit_is_clamped():
    assert clamp_limit(None) == 5
    assert clamp_limit(0) == 1
    assert clamp_limit(-3) == 1
    assert clamp_limit(9999) == MAX_LIMIT


def test_unknown_category_names_the_valid_values(dataset):
    with pytest.raises(ValueError) as exc:
        search(dataset, keywords=["용접"], category="nonsense")
    assert "confined-space" in str(exc.value)


def test_category_filter_matches_enum(dataset):
    payload = search(dataset, category="confined-space", limit=MAX_LIMIT)
    assert payload["results"]
    for entry in payload["results"]:
        assert entry["category"] == "confined-space"


def test_unverified_mapping_is_flagged_not_hidden(dataset):
    """An unverified entry must look different from a verified one."""
    mapping = next(iter(dataset.mappings.values()))
    laws = dataset.laws
    verified = format_mapping(mapping, laws)
    assert verified["verification"]

    unverified = format_mapping(mapping.model_copy(update={"last_verified": None}), laws)
    assert unverified["verification"] == UNVERIFIED


def test_categories_cover_the_full_vocabulary(dataset):
    payload = categories(dataset)
    got = {c["category"] for c in payload["categories"]}
    assert got == {c.value for c in WorkCategory}


def test_categories_examples_come_from_data(dataset):
    payload = categories(dataset)
    by_cat = {c["category"]: c for c in payload["categories"]}
    confined = by_cat["confined-space"]
    assert confined["mapping_count"] == len(confined["work_types"])
    assert "밀폐공간 용접" in confined["work_types"]


def test_article_count_matches_articles(dataset):
    payload = search(dataset, keywords=["밀폐공간"], limit=MAX_LIMIT)
    for entry in payload["results"]:
        assert entry["article_count"] == len(entry["articles"])


# --- MCP wiring (needs the optional dependency) --------------------------


def test_server_registers_the_three_tools():
    pytest.importorskip("mcp.server.mcpserver")
    server = build_server()
    import anyio

    tools = anyio.run(server.list_tools)
    names = {t.name for t in tools}
    assert names == {"search_laws", "get_mapping", "list_categories"}


def test_every_tool_has_a_description():
    pytest.importorskip("mcp.server.mcpserver")
    server = build_server()
    import anyio

    tools = anyio.run(server.list_tools)
    for t in tools:
        assert t.description and len(t.description) > 40, t.name


def test_bad_category_message_reaches_the_model():
    """A ValueError would be scrubbed to 'Error executing tool'. The model has
    to see the valid values to correct its own call, so the tool raises
    ToolError instead."""
    pytest.importorskip("mcp.server.mcpserver")
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

    import anyio

    server = build_server()

    async def call():
        return await server.call_tool(
            "search_laws", {"keywords": ["용접"], "category": "nonsense"}
        )

    with pytest.raises(ToolError) as exc:
        anyio.run(call)
    assert not isinstance(exc.value, UnexpectedToolError)
    assert "confined-space" in str(exc.value)


def test_unknown_mapping_id_message_reaches_the_model():
    pytest.importorskip("mcp.server.mcpserver")
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

    import anyio

    server = build_server()

    async def call():
        return await server.call_tool("get_mapping", {"mapping_id": "no-such-mapping"})

    with pytest.raises(ToolError) as exc:
        anyio.run(call)
    assert not isinstance(exc.value, UnexpectedToolError)
    assert "no-such-mapping" in str(exc.value)
