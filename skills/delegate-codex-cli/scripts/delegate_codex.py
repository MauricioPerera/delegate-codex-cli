#!/usr/bin/env python3
"""Run one isolated, ephemeral Codex CLI goal with explicit parameters."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True, help="Goal and observable success criteria")
    parser.add_argument(
        "--role",
        choices=("pm", "dev", "qa-fast", "qa-critical"),
        help="Role preset that selects a model and operation",
    )
    parser.add_argument("--model", help="Codex model slug; overrides the profile default")
    parser.add_argument("--cwd", required=True, help="Child agent workspace")
    parser.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write", "danger-full-access"),
        default="workspace-write",
    )
    parser.add_argument("--timeout", type=int, default=900, help="Timeout in seconds")
    parser.add_argument("--output", help="File for the child agent's final message")
    parser.add_argument("--profile", help="Optional Codex config profile")
    parser.add_argument("--kdd-root", help="KDD repository root for context inputs")
    parser.add_argument(
        "--kdd-prefix",
        action="append",
        default=[],
        help="KDD-relative static file to prepend; repeat in exact desired order",
    )
    parser.add_argument(
        "--kdd-contract",
        help="KDD context contract JSON; runs scripts/assemble_context.py",
    )
    parser.add_argument("--config", action="append", default=[], help="Repeated key=value override")
    parser.add_argument("--image", action="append", default=[], help="Repeated image path")
    parser.add_argument("--skip-git-repo-check", action="store_true")
    parser.add_argument("--no-ephemeral", action="store_true", help="Allow session persistence")
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Bypass approvals and sandboxing; use only with explicit authorization",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codex = shutil.which("codex")
    if not codex:
        print("codex was not found on PATH", file=sys.stderr)
        return 127

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        print(f"Child workspace does not exist: {cwd}", file=sys.stderr)
        return 2

    prompt = build_prompt(args, cwd)

    profile_models = {
        "pm": "gpt-5.6-terra",
        "dev": "gpt-5.6-sol",
        "qa-fast": "gpt-5.6-luna",
        "qa-critical": "gpt-5.6-terra",
    }
    model = args.model or profile_models.get(args.role, "gpt-5.6-luna")
    is_review = args.role == "qa-critical"
    command = [codex, "exec"]
    if is_review:
        command.append("review")
    command.extend(["--model", model, "--json"])
    if not is_review:
        command.extend(["--cd", str(cwd)])
    if is_review:
        command.append("--uncommitted")
    if not args.no_ephemeral:
        command.append("--ephemeral")
    if args.unsafe:
        command.append("--dangerously-bypass-approvals-and-sandbox")
    elif not is_review:
        command.extend(["--sandbox", args.sandbox])
    if args.profile:
        command.extend(["--profile", args.profile])
    if args.skip_git_repo_check:
        command.append("--skip-git-repo-check")
    for override in args.config:
        command.extend(["--config", override])
    for image in args.image:
        command.extend(["--image", image])
    if args.output:
        command.extend(["--output-last-message", str(Path(args.output).expanduser().resolve())])

    try:
        completed = subprocess.run(command + [prompt], cwd=cwd, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"Codex child timed out after {args.timeout}s", file=sys.stderr)
        return 124
    except OSError as exc:
        print(f"Failed to launch Codex: {exc}", file=sys.stderr)
        return 126
    return completed.returncode


def build_prompt(args: argparse.Namespace, cwd: Path) -> str:
    """Build a stable KDD prefix followed by the variable goal."""
    root = Path(args.kdd_root).expanduser().resolve() if args.kdd_root else cwd
    sections = []

    for relative in args.kdd_prefix:
        path = (root / relative).resolve()
        if not path.is_file():
            raise SystemExit(f"KDD prefix file does not exist: {path}")
        content = path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
        label = path.relative_to(root).as_posix()
        sections.append(f"--- KDD_STATIC_FILE: {label} ---\n{content}")

    if args.kdd_contract:
        contract = (root / args.kdd_contract).resolve()
        assembler = root / "scripts" / "assemble_context.py"
        if not contract.is_file():
            raise SystemExit(f"KDD contract does not exist: {contract}")
        if not assembler.is_file():
            raise SystemExit(f"KDD assembler does not exist: {assembler}")
        result = subprocess.run(
            [sys.executable, str(assembler), str(contract), args.goal, "-v"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise SystemExit(f"KDD context assembly failed ({result.returncode}): {detail}")
        start = result.stdout.find("--- context ---")
        end = result.stdout.find("--- /context ---", start + 1)
        if start < 0 or end < 0:
            raise SystemExit("KDD assembler output did not contain context markers")
        sections.append(result.stdout[start + len("--- context ---"):end].strip())

    if not sections:
        return args.goal
    static_prefix = "\n\n".join(sections)
    return (
        "KDD_CONTEXT_V1\n"
        + static_prefix
        + "\n\n--- DYNAMIC_GOAL ---\n"
        + args.goal
    )


if __name__ == "__main__":
    raise SystemExit(main())
