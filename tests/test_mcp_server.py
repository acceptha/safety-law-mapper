"""MCP wiring, plus the protocol round-trip: what a client receives over MCP
must equal what REST serves. The payload shapes themselves are tested in test_view."""

import pytest

from safety_law_mapper.mcp_server import build_server


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
    import anyio
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

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
    import anyio
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

    server = build_server()

    async def call():
        return await server.call_tool("get_mapping", {"mapping_id": "no-such-mapping"})

    with pytest.raises(ToolError) as exc:
        anyio.run(call)
    assert not isinstance(exc.value, UnexpectedToolError)
    assert "no-such-mapping" in str(exc.value)


# --- the contract that matters: what an LLM gets over MCP is what REST serves


def _call_over_mcp(name: str, arguments: dict) -> dict:
    """Round-trip one tool call through the real MCP protocol (in-process
    client ↔ server), not through the registered function directly, so the
    wire-level envelope is exercised too."""
    import anyio
    from mcp import Client

    async def call():
        async with Client(build_server()) as client:
            result = await client.call_tool(name, arguments)
            assert result.is_error is False, result.content
            return result.structured_content

    return anyio.run(call)


def test_search_laws_over_mcp_matches_rest_search():
    """Both interfaces build responses in `view`; a reimplementation of either
    one shows up here as a payload mismatch, article by article."""
    pytest.importorskip("mcp.client.client")
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from safety_law_mapper.api import app

    over_mcp = _call_over_mcp(
        "search_laws", {"keywords": ["밀폐공간", "용접"], "limit": 5}
    )
    over_http = (
        TestClient(app)
        .get("/search", params={"q": ["밀폐공간", "용접"], "limit": 5})
        .json()
    )

    assert over_mcp == over_http
    assert over_mcp["results"][0]["mapping_id"] == "confined-space-welding"


def test_get_mapping_over_mcp_returns_verified_citations():
    pytest.importorskip("mcp.client.client")
    from safety_law_mapper import DISCLAIMER
    from safety_law_mapper.view import GROUNDING_RULE, UNVERIFIED

    payload = _call_over_mcp("get_mapping", {"mapping_id": "confined-space-welding"})

    assert payload["mapping_id"] == "confined-space-welding"
    assert payload["verification"] != UNVERIFIED
    assert payload["article_count"] == len(payload["articles"]) > 0
    for art in payload["articles"]:
        assert art["source_url"].startswith("https://www.law.go.kr")
        assert art["article_ref"]
    assert payload["grounding"] == GROUNDING_RULE
    assert payload["disclaimer"] == DISCLAIMER


def test_list_categories_over_mcp_covers_the_vocabulary():
    """Every category the model may pass to search_laws is listed, and each
    one is backed by real mappings — not a vocabulary the engine cannot serve."""
    pytest.importorskip("mcp.client.client")
    from safety_law_mapper.models import WorkCategory
    from safety_law_mapper.view import categories, get_dataset

    payload = _call_over_mcp("list_categories", {})

    assert {c["category"] for c in payload["categories"]} == {
        c.value for c in WorkCategory
    }
    for entry in payload["categories"]:
        assert entry["mapping_count"] == len(entry["work_types"]) > 0
    assert payload == categories(get_dataset())
