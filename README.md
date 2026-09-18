# opencode-free-repair

Repair skill for [Hermes Agent](https://hermes-agent.nousresearch.com) when **OpenCode free-tier models** (`muse-spark-*-contributor-free`) break:

- `400 / MissingSessionID` — *"OpenCode's free tier can only be used in OpenCode"*
- `403` generic fingerprint rejection
- the model vanishing from the picker

The OpenCode relay (`https://opencode.ai/zen/v1`) only serves the free tier to requests that fingerprint like the **official OpenCode client** — and it tightens those checks silently over time. This skill captures what the official client actually sends, diffs it against what Hermes sends, bisects any new gates, and patches Hermes to match.

## Install

Copy into your Hermes skills directory:

```bash
git clone https://github.com/MelvernMogens/opencode-free-repair.git \
  ~/.hermes/skills/software-development/opencode-free-repair
```

Or just copy `SKILL.md` anywhere under `~/.hermes/skills/`.

## What it does

1. Reproduce the failure and classify the gate (identity vs fingerprint)
2. Sanity-check the model itself with the official OpenCode CLI
3. Capture the official client's request via a local catch-proxy
4. Diff the fingerprint: User-Agent, `x-opencode-client`, credential, ID formats, body shape, native tool names
5. Bisect unknown gates by mutating one field at a time against the real relay
6. Patch the relevant Hermes files (with backups)
7. Test: pytest + direct SDK request + real `hermes -z` run
8. Fix config, restart the backend safely, verify in the UI

## Run the repair with any model

The repair agent doesn't need muse-spark — any capable model works, so the broken provider never blocks its own fix:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/hermes --provider zai --model glm-5.3 \
  'Load skill opencode-free-repair and run it end to end.'
```

## Requirements

- Hermes Agent checkout at `~/.hermes/hermes-agent` with `uv`
- Read the full procedure in [`SKILL.md`](SKILL.md) — it is the source of truth
