---
type: 'Task Contract'
title: 'Deterministic prompt prefix'
description: 'Freeze the existing prompt ordering oracle.'
tags: ['kdd', 'prompt', 'pilot']
task: deterministic-prompt-prefix
intent: 'Preserve deterministic prompt ordering.'
target: 'skills/delegate-codex-cli/scripts/delegate_codex.py'
signature: 'def build_prompt(args: argparse.Namespace, cwd: Path) -> str:'
test_command: 'python -m unittest pilot_oracles/prompt.py'
test_runner: python-unittest
oracle_files: ['pilot_oracles/prompt.py', 'tests/test_skill.py']
budget:
  cyclomatic_max: 12
  nesting_max: 3
tests: 'pilot_oracles/prompt.py'
tests_sha256: '1add7d2198da99f60cdf2c6f1935356f8c36aee77cf6e8e0ea58da2b3e1fb8b5'
touch_only: ['skills/delegate-codex-cli/scripts/delegate_codex.py']
deps_allowed: []
forbids: ['network']
---

# Deterministic prompt prefix

## Intent

Keep the static context stable for the same input and append the variable goal. The [pilot protocol](../../pilot.md) explains how to verify this case across environments.

## Interface

```python
def build_prompt(args: argparse.Namespace, cwd: Path) -> str:
```

## Invariants

- Static files appear in the caller's supplied order.
- Identical inputs produce identical text and digest.
- The goal appears at the end.

## Examples

- `kdd_prefix=["a.md", "b.md"]` with goal `"dynamic goal"` places `a.md` before `b.md` and ends with `"dynamic goal"`.

- With no static files and no contract, the prompt is the goal verbatim.

## Do / Don't

- DO keep prefix files in the caller's order.
- DON'T modify the sealed oracle to make a regression pass.

## Tests

The managed runner executes the original ordering assertion through `pilot_oracles/prompt.py`. The original suite retains the case in `tests/test_skill.py`.

## Constraints

PARAR y reportar si el cambio exige editar el oráculo. Preserve the existing API and the sealed test. Exercise the regression by editing production in a dedicated pilot commit and then reverting that commit.
