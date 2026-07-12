---
name: delegate-codex-cli
description: Delegate a concrete goal to an ephemeral local Codex CLI instance with an explicit model, workspace, sandbox, output format, and timeout. Use when a task should be executed or validated by a separate Codex agent, especially for isolated coding, small proofs of concept, repository checks, or independent implementation passes.
---

# Delegate Codex CLI

Use this skill to run a separate, ephemeral Codex CLI agent for a well-scoped goal. The parent agent remains responsible for choosing the workspace, permissions, success criteria, and interpreting the child result.

## Profiles

Use one of these role presets with `--role` when the user does not need to choose every flag manually:

| Role | Preset | Default model | Operation |
| --- | --- | --- | --- |
| Project Manager | `pm` | `gpt-5.6-terra` | `codex exec` for requirements, decomposition, prioritization, and goal definition |
| Developer | `dev` | `gpt-5.6-sol` | `codex exec` for implementation, architecture, and debugging |
| Quality Assurance | `qa-fast` | `gpt-5.6-luna` | `codex exec` for syntax, lint, unit-test, and structural checks |
| Quality Assurance | `qa-critical` | `gpt-5.6-terra` | `codex exec review --uncommitted` for business intent, edge cases, and logic risks |

Treat these as routing defaults, not guarantees about capability, latency, or price. Override the model with `--model` when the user requests another catalog slug.

## Workflow

1. Convert the request into one concrete goal with observable completion criteria. Keep the goal self-contained; include relevant paths, tests, and required final report fields.
2. Choose the model explicitly. Use the locally available catalog when the user names a model or when the default is uncertain:
   `codex debug models`.
3. Choose a workspace explicitly with `--cwd`. Prefer an isolated directory or worktree for experiments and potentially conflicting changes.
4. Use `--sandbox workspace-write` by default. Use `read-only` for inspection-only work. Use `--unsafe` only when the user explicitly authorizes unrestricted execution and the workspace is isolated.
5. Run the bundled wrapper:

   ```powershell
   python "$env:CODEX_HOME\skills\delegate-codex-cli\scripts\delegate_codex.py" `
     --role dev `
     --goal "<goal and success criteria>" `
     --cwd "<workspace>" `
     --sandbox workspace-write `
     --timeout 900
   ```

   When `CODEX_HOME` is unset, use the discovered installation directory for this skill. Do not hard-code a user name, home directory, or operating-system-specific path into automation.
6. Inspect the JSONL events and the final message. Independently verify important artifacts, tests, and exit status; do not treat a child claim as proof by itself.
7. Report the selected model, workspace, session id when present, exit status, artifacts, and any sandbox or permission failure.

## Parameters

The wrapper supports `--role pm|dev|qa-fast|qa-critical`, `--goal`, `--model`, `--cwd`, `--sandbox`, `--timeout`, `--output`, `--profile` for a Codex config profile, repeated `--config`, repeated `--image`, `--skip-git-repo-check`, `--no-ephemeral`, and `--unsafe`. A role supplies the default model; an explicit `--model` wins. `qa-critical` uses `codex exec review --uncommitted` and reviews the current repository changes. The wrapper always requests JSONL output and uses ephemeral sessions unless explicitly disabled.

### KDD context

When the child workspace is a KDD repository, use `--kdd-root` plus repeated `--kdd-prefix` paths to prepend static knowledge and contracts in an explicit, stable order:

```powershell
python ...\delegate_codex.py `
  --role dev `
  --kdd-root "C:\repo" `
  --kdd-prefix ".agents/AGENTS.md" `
  --kdd-prefix "knowledge/OKF-SPEC.md" `
  --kdd-prefix "knowledge/metodologia-ejecucion.md" `
  --kdd-prefix "knowledge/contracts/mi-tarea.md" `
  --goal "Implementa el contrato mi-tarea y verifica su test_command." `
  --cwd "C:\repo"
```

Use `--kdd-contract ccdd/context.json` to invoke KDD's `scripts/assemble_context.py` with the goal, preserving its budget and guardrails, and inject the extracted assembled context. This is useful for task-aware retrieval, but `okf_nodes` can vary with the task and therefore may change the prefix. Use ordered `--kdd-prefix` files when exact prefix stability is the priority.

Keep static KDD content before the dynamic goal, use identical file order and normalized line endings, and avoid timestamps, random IDs, or changing reports in the prefix. Prompt caching is an optimization to measure, not a completion guarantee: official API guidance requires an exact prefix and recommends a stable `prompt_cache_key` for GPT-5.6-family requests, while the current Codex CLI wrapper does not expose a dedicated cache-key flag. Do not claim a fixed discount unless the actual execution path exposes and confirms `cached_tokens` and `cache_write_tokens`.

Do not pass secrets in the goal, KDD prefix, or command line. Prefer environment variables or files already authorized in the child workspace. Run KDD guardrails before delegating when a contract is available. Do not use `--unsafe` to work around an unexplained failure; first report or fix the sandbox/configuration issue.

## Failure handling

- If `codex` is missing, stop and report that the Codex CLI is not installed or not on `PATH`.
- If the model is rejected, list the catalog from `codex debug models` and retry only with a model the user approves.
- If the sandbox helper fails, report the exact error. Retry with `--unsafe` only when explicitly authorized and only in an isolated workspace.
- If the child exits nonzero or times out, preserve its JSONL output and report the failure without claiming completion.
- If the child succeeds, verify the requested artifact or test from the parent environment whenever practical.

## Recommended routing

Send requirements clarification, task breakdown, acceptance criteria, and goal creation to `pm`. Send code changes and technical implementation to `dev`. Run `qa-fast` after implementation for automated checks, then `qa-critical` for a repository review against the PM's acceptance criteria. Pass the PM's output into later goals explicitly through the prompt or a file in the child workspace.
