# Delegate Codex CLI

Portable Codex skill for delegating explicit goals to ephemeral local Codex CLI workers. It supports role-based model routing, safe workspace policies, JSONL output, timeouts, and optional KDD context assembly.

## Install

Copy `skills/delegate-codex-cli` into your Codex skills directory:

```text
$CODEX_HOME/skills/delegate-codex-cli
```

If `CODEX_HOME` is not set, use the Codex home directory for your operating system. The skill and wrapper do not depend on a specific user name, home path, or shell.

## Usage

```bash
python "$CODEX_HOME/skills/delegate-codex-cli/scripts/delegate_codex.py" \
  --role dev \
  --goal "Implement the requested change and run its tests." \
  --cwd "/path/to/repository" \
  --sandbox workspace-write
```

Role defaults are:

- `pm` -> `gpt-5.6-terra`
- `dev` -> `gpt-5.6-sol`
- `qa-fast` -> `gpt-5.6-luna`
- `qa-critical` -> `gpt-5.6-terra` with `codex exec review --uncommitted`

Override a role model with `--model`. Use `--unsafe` only for an explicitly authorized isolated workspace.

## KDD

Prepend stable KDD files in a controlled order:

```bash
python "$CODEX_HOME/skills/delegate-codex-cli/scripts/delegate_codex.py" \
  --role dev \
  --kdd-root "/path/to/kdd-repository" \
  --kdd-prefix ".agents/AGENTS.md" \
  --kdd-prefix "knowledge/OKF-SPEC.md" \
  --kdd-prefix "knowledge/metodologia-ejecucion.md" \
  --kdd-prefix "knowledge/contracts/task.md" \
  --goal "Implement task.md and verify its test_command." \
  --cwd "/path/to/kdd-repository"
```

Use `--kdd-contract ccdd/context.json` to invoke KDD's deterministic context assembler with its budget and guardrails. Task-aware `okf_nodes` retrieval can change the prefix between tasks; use ordered `--kdd-prefix` files when exact prefix stability is the priority.

Prompt caching is an optimization to measure, not a fixed discount guarantee. Keep static content first and dynamic goals last, and verify cache metrics through the execution surface that exposes them.

## Development

```bash
python -m unittest discover -s tests -v
```

The package has no third-party Python dependencies.
