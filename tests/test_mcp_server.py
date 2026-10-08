"""MCP wiring only. The payloads these tools return are tested in test_view."""

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
