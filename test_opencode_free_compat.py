"""Regression coverage for OpenCode contributor-tier request identity."""

from agent.opencode_affinity import merge_opencode_session_headers, opencode_session_headers
from agent.transports.codex import _alias_wire_tools


def test_opencode_free_adds_native_tool_aliases_without_removing_hermes_tools():
    tools = [
        {"type": "function", "name": "terminal", "parameters": {"type": "object"}},
        {"type": "function", "name": "read_file", "parameters": {"type": "object"}},
    ]
    wire, aliases = _alias_wire_tools(tools, {"provider": "opencode-free"}, False)

    assert {tool["name"] for tool in wire} == {"terminal", "read_file", "bash", "read"}
    assert aliases["bash"] == "terminal"
    assert aliases["read"] == "read_file"


def test_opencode_free_keeps_provider_profile_session_identity():
    assert opencode_session_headers(
        "opencode-free", "https://opencode.ai/zen/v1", "20260917_invalid_hermes_id"
    ) == {}

    kwargs = {}
    merge_opencode_session_headers(
        kwargs, "opencode-free", "https://opencode.ai/zen/v1", "20260917_invalid_hermes_id"
    )
    assert "extra_headers" not in kwargs


def test_paid_opencode_keeps_conversation_affinity(monkeypatch):
    monkeypatch.setattr(
        "agent.portal_tags.get_affinity_scope", lambda: None
    )
    monkeypatch.setattr(
        "agent.portal_tags.get_conversation_context", lambda: None
    )
    assert opencode_session_headers(
        "opencode-zen", "https://opencode.ai/zen/v1", "conversation-123"
    ) == {"x-opencode-session": "conversation-123"}
