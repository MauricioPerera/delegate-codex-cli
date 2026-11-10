---
type: 'Concept'
title: 'KDD validator pilot'
description: 'Use one pinned validator for an existing Python project.'
tags: ['kdd', 'pilot', 'validation']
---

# KDD validator pilot

The existing Python suite defines the prompt behavior. The [prompt contract](contracts/pilot/prompt.md) selects one existing case through a sealed adapter outside the original suite. The adapter selects the same test method and adds no assertions.

## Validator and evidence contract

- The consumer tracks a single 40-hex commit in `.kdd/validator.lock`. Codex, terminal and GitHub Actions enter through `python .kdd/validate.py` at the root. Python 3.11 and Git are required.
- The launcher uses the public `MauricioPerera/KDD` origin. It resolves the exact commit, materializes its Git tree into private temporary storage outside the consumer, and verifies the files against that tree before execution. An absent, invalid, unavailable or mismatched pin, or a mismatched file, fails before validator execution. Each run fetches the pin and cleans its temporary files.
- The pinned tooling checks the contract and its seal, the OKF index and the one managed `unittest` case. Missing evidence, zero cases and skips fail. The final JSON line starts with `KDD_PILOT ` and includes the requested and verified KDD SHAs, actual consumer SHA, checkout status, contract and seal, Python, command, stage and result.
- If a KDD quality policy exists at `quality/product.json` or `quality.json`, the pinned quality verifier requires `KDD_QUALITY_APPROVED_REF` from the consumer. The approved commit must be available locally with its required files. If both paths are present the configuration is ambiguous and fails.

## Integration contract

- This adoption adds a workflow, launcher, lock, guidance and contract files without editing the original suite or its workflow. Adding the same files with identical bytes is a no-op. Conflicting adoption paths are detected before writes.
- For the pilot branch, Actions checks out the pushed consumer commit on Ubuntu and Windows. Three clean consumer commits whose pin progresses A, B, A must produce the corresponding verified SHA in Codex, the terminal and each runner. Only the pin changes in the last two commits.
- At the restored A pin, reversing the order of the static prefix in production must fail the existing ordering assertion. A Git revert must return the same case to green. The contract and its test files retain the same bytes throughout. Changing the seal alone is rejected even while the original product suite passes.
