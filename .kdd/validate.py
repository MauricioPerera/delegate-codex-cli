"""Validate the consumer with the single KDD commit selected by its lock."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://github.com/MauricioPerera/KDD.git"
CONTRACT = Path("knowledge/contracts/pilot/prompt.md")
PIN = re.compile(r"[0-9a-f]{40}")


class Rejected(Exception):
    """A precondition or a validation stage failed."""


def git(root, env, *args, binary=False):
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), *args],
        env=env, capture_output=True, timeout=120, check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise Rejected(f"Git {args[0]} failed ({result.returncode}): {detail}")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def clean_git_environment():
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    return env


def blob_manifest(raw):
    manifest = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise Rejected(f"Unsupported entry in the pinned tree: {name!r}")
        manifest[name.decode("utf-8")] = oid.decode("ascii")
    return manifest


def git_blob_hash(data):
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def materialize(archive, manifest, destination):
    with tarfile.open(archive, "r:") as snapshot:
        for entry in snapshot:
            if entry.isdir():
                continue
            path = PurePosixPath(entry.name)
            if (not entry.isfile() or path.is_absolute()
                    or any(part == ".." or ":" in part or "\\" in part for part in path.parts)
                    or entry.name not in manifest):
                raise Rejected(f"Unexpected entry in the validator archive: {entry.name}")
            with snapshot.extractfile(entry) as source:
                data = source.read()
            if git_blob_hash(data) != manifest.pop(entry.name):
                raise Rejected(f"Validator blob differs from Git: {entry.name}")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
    if manifest:
        raise Rejected(f"Validator archive omits Git blob: {next(iter(manifest))}")


def prepare_validator(directory, pin):
    repository = directory / "git"
    repository.mkdir()
    env = clean_git_environment()
    git(repository, env, "init", "--bare", "--template=")
    git(repository, env, "fetch", "--depth=1", "--no-tags", "--no-recurse-submodules", ORIGIN, pin)
    actual = git(repository, env, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if actual != pin or git(repository, env, "cat-file", "-t", pin) != "commit":
        raise Rejected(f"Fetched validator {actual} does not match commit {pin}")
    manifest = blob_manifest(git(repository, env, "ls-tree", "-rz", "--full-tree", pin, binary=True))
    archive = directory / "validator.tar"
    git(repository, env, "archive", "--format=tar", f"--output={archive}", pin)
    validator = directory / "validator"
    materialize(archive, manifest, validator)
    return actual, validator


def run_gate(validator, name, *arguments):
    script = validator / "scripts" / name
    result = subprocess.run(
        [sys.executable, "-E", "-s", "-B", "-X", "utf8", str(script), *arguments],
        cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
        timeout=180, check=False,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode:
        raise Rejected(f"{name} exited {result.returncode}")
    return result.stdout


def oracle_fields():
    frontmatter = (ROOT / CONTRACT).read_text(encoding="utf-8").split("---", 2)[1]
    fields = {}
    for name in ("test_command", "tests_sha256"):
        match = re.search(rf"^{name}: '([^'\n]+)'$", frontmatter, re.MULTILINE)
        if match is None:
            raise Rejected(f"Missing pilot contract field: {name}")
        fields[name] = match[1]
    return fields


def quality_check(validator):
    policies = [path for path in ("quality/product.json", "quality.json") if (ROOT / path).exists()]
    if not policies:
        return None
    if len(policies) != 1:
        raise Rejected("Select one KDD quality policy")
    reference = os.environ.get("KDD_QUALITY_APPROVED_REF", "")
    if not PIN.fullmatch(reference):
        raise Rejected("KDD_QUALITY_APPROVED_REF must be a full approved consumer commit SHA")
    run_gate(validator, "verify_quality.py", "--repo-root", ".", "--policy", policies[0],
             "--approved-ref", reference)
    return reference


def validate(record):
    record["stage"] = "pin"
    pin = (ROOT / ".kdd/validator.lock").read_text(encoding="ascii").removesuffix("\n")
    if not PIN.fullmatch(pin):
        raise Rejected("validator.lock must contain one lowercase 40-digit commit SHA")
    record["requested_kdd_sha"] = pin
    record["stage"] = "consumer"
    if sys.version_info[:2] != (3, 11):
        raise Rejected("The pilot requires Python 3.11")
    if Path(git(ROOT, None, "rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise Rejected("The launcher is outside the consumer Git root")
    record["consumer_sha"] = git(ROOT, None, "rev-parse", "--verify", "HEAD")
    record["dirty"] = bool(git(ROOT, None, "status", "--porcelain"))
    record["stage"] = "resolve"
    with tempfile.TemporaryDirectory(prefix="kdd-pilot-") as temporary:
        actual, validator = prepare_validator(Path(temporary), pin)
        record["verified_kdd_sha"] = actual
        record["stage"] = "contract"
        if list((ROOT / CONTRACT.parent).rglob("*.md")) != [ROOT / CONTRACT]:
            raise Rejected("The pilot requires exactly its declared prompt contract")
        record.update(oracle_fields())
        run_gate(validator, "validate_contracts.py", "--repo-root", ".", CONTRACT.as_posix())
        record["stage"] = "okf"
        run_gate(validator, "validate_okf.py", "knowledge")
        record["stage"] = "quality"
        record["quality_approved_ref"] = quality_check(validator)
        record["stage"] = "oracle"
        output = run_gate(validator, "validate_test_commands.py", CONTRACT.parent.as_posix(), ".")
        results = re.findall(r"^  oracle_execution: runner=(\S+) executed_tests=(\d+)$",
                             output, re.MULTILINE)
        if results != [("python-unittest", "1")]:
            raise Rejected("Expected evidence of exactly one managed unittest case")
        record["executed_tests"] = 1


def main():
    record = {"contract": CONTRACT.as_posix(), "python": sys.version.split()[0]}
    try:
        validate(record)
    except (OSError, ValueError, IndexError, Rejected, subprocess.SubprocessError, tarfile.TarError) as error:
        record.update(result="fail", error=str(error))
    else:
        record.update(stage="complete", result="pass")
    print("KDD_PILOT " + json.dumps(record, sort_keys=True), flush=True)
    return int(record["result"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
