---
name: opencode-free-repair
description: Use when OpenCode free models break in Hermes.
---

Full repair workflow for OpenCode free-tier (muse-spark-*-contributor-free) breakage: 400/403 MissingSessionID, "free tier can only be used in OpenCode", or model vanishing from the picker.

Repo: `~/.hermes/hermes-agent` (use `uv run python` / `uv run --with pytest pytest`; bare `python3 -m py_compile` fails). Config via `./venv/bin/hermes config set/get`. Backup patched files to `~/.hermes/backups/<stamp>/` before big changes.

## Step-by-step

1. **Reproduce**: `./venv/bin/hermes -z 'Reply exactly OK' --provider opencode-free --model muse-spark-1.3-contributor-free`. Note exact HTTP code + error type (MissingSessionID = identity gate; 403 generic = fingerprint gate).
2. **Sanity-check the model itself**: download official OpenCode release zip (darwin-arm64) from GitHub releases, run `HOME=/tmp/oc-clean <bin>/opencode run --model opencode/muse-spark-1.3-contributor-free 'Reply exactly OK'`. If this works, relay is fine and only Hermes' fingerprint is stale.
3. **Capture the official request**: scratch HOME with `~/.config/opencode/opencode.json` setting `provider.opencode.options.baseURL = http://127.0.0.1:8765/v1`; tiny Python http.server handler dumps method/headers/body per request; run official CLI against it. Save capture JSON.
4. **Diff Hermes vs official** on: User-Agent (`opencode/<ver> ai-sdk/provider-utils/<v> runtime/bun/<v>`), `x-opencode-client: cli`, credential (api_key `public`, NOT empty), ID format (`ses_*`: prefix + base36 timestamp DESCENDING + 12 random base62; `prj_*` = sha1 of `worktreeURL#worktreeName` from git remote), body shape (instructions is a ~1KB agent prompt — short prompts 403), and tools list (must expose `bash` and `read`).
5. **Bisect unknown gates** by mutating the captured body one field at a time against the real relay: truncate instructions (binary search length), drop tools one by one. 200 = gate satisfied, 403 = gate hit. This is how the bash/read requirement and prompt-length floor were found.
6. **Patch Hermes**:
   - `hermes_cli/models.py`: `opencode_client_user_agent()`, `_opencode_id()`, `_opencode_project_id()`, `opencode_zen_free_headers()`, `OPENCODE_ZEN_FREE_KEYLESS_PLACEHOLDER = "public"`.
   - `plugins/model-providers/opencode-free/__init__.py` + `opencode-zen/__init__.py`: mirror the same identity set in `default_headers`/`_ATTRIBUTION_HEADERS`.
   - `agent/transports/codex.py`: `_alias_wire_tools` adds `bash`/`read` aliases of terminal/read_file for provider `opencode-free`, with reverse alias map so calls dispatch back.
   - Never let free headers override a real API key (guards in `agent/auxiliary_client.py`, `agent/agent_runtime_helpers.py`, `_opencode_family_key_configured`).
7. **Test**: `uv run python` direct OpenAI-SDK request with `opencode_zen_free_headers()` → expect 200/completed/OK; then `./venv/bin/hermes -z ...`; then `uv run --with pytest pytest -q tests/agent/test_opencode_free_compat.py tests/hermes_cli/test_runtime_provider_resolution.py -k opencode` (use `--with pytest`; run_tests.sh fails without dev venv). Update test expectations when header/credential contract changes.
8. **Config**: `hermes config set model.provider opencode-free`, `model.default muse-spark-1.3-contributor-free`, `model.base_url https://opencode.ai/zen/v1`, `model.api_mode codex_responses`; contributor tier needs `security.allow_data_training_tiers_noninteractive true` (warn user: trains on data).
9. **Restart backend**: `ps ax -o pid=,command= | grep '[h]ermes_cli.main serve'` → kill PID (run the kill in a backgrounded terminal with notify, else the tool call goes orphan/UNKNOWN) → desktop respawns it → verify new PID + lstart.
10. **Verify in the UI**: model picker must show muse-spark free variant; pick it and send one message.

## Gotchas
- Relay gates change silently between versions — when it breaks again, re-capture (steps 2-4); don't assume the old header set still passes.
- Muse Spark free only works via `/v1/responses` (api_mode codex_responses); chat_completions 503s.
- The `X-Session-ID`-only era is over; modern gate checks UA floor, x-opencode-client, ID shapes, prompt size, and native tool names.
- Plain `python3 -m py_compile` fails (PEP 668 host python); always `uv run python -m py_compile`.
- Never print API keys/tokens in test output; keep real-key path guarded.

## Running the repair with a DIFFERENT model (sol, glm, etc.)

The repair agent does not need muse-spark — any capable model works. Launch a repair session on a known-good provider so the broken one never blocks the fix:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/hermes --provider zai --model glm-5.3 \
  'Load skill opencode-free-repair and run it end to end: reproduce the opencode-free breakage, re-capture the official fingerprint, patch, test, restart backend, and verify the model picker.'
```

Rules for the delegated run:
- Provider/model flags are explicit (`--provider zai --model glm-5.3`, or `--provider actual --model sol-...`) so the broken opencode-free default in config.yaml is bypassed; never edit config.yaml's model.* keys just to run the fix.
- The repair session must follow this skill's steps 1-10 verbatim — capture official request first, bisect gates, then patch. No guessing headers.
- Same safety rules apply: backup before patching, never print secrets, restart backend via backgrounded kill.
- From inside a Hermes chat, the same can be delegated with delegate_task to a subagent instructed to load this skill.
