#!/usr/bin/env python3
"""Initialize a shared CUMCM v2 workspace without overwriting user artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_ROOT / "templates" / "shared"
DIRECTORIES = (
    "input/data",
    "state/handoffs",
    "artifacts",
    "literature/notes",
    "code",
    "results",
    "figures",
    "reviews",
    "reviews/subagents/stage_01",
    "reviews/subagents/stage_03",
    "reviews/subagents/stage_05",
    "paper_workspace",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def input_fingerprint(input_dir: Path) -> str | None:
    files = sorted(path for path in input_dir.rglob("*") if path.is_file())
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(input_dir).as_posix().encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def initialize(workspace: Path, competition: str = "cumcm") -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        (workspace / relative).mkdir(parents=True, exist_ok=True)

    state_path = workspace / "state" / "workflow.json"
    if state_path.exists():
        raise FileExistsError(f"工作流已存在，拒绝覆盖: {state_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    fingerprint = input_fingerprint(workspace / "input")
    workflow = json.loads((TEMPLATE_ROOT / "workflow_state.json").read_text(encoding="utf-8"))
    workflow.update(
        competition=competition,
        run_id=run_id,
        input_fingerprint=fingerprint,
        updated_at=utc_now(),
    )
    if fingerprint is None:
        workflow["blocking_issues"] = ["input/ 中尚未发现题面或附件；Stage 0 开始前需要补充。"]
    write_json(state_path, workflow)

    copies = {
        TEMPLATE_ROOT / "capabilities.json": workspace / "state" / "capabilities.json",
        TEMPLATE_ROOT / "artifact_manifest.json": workspace / "state" / "artifact_manifest.json",
        TEMPLATE_ROOT / "run_manifest.json": workspace / "artifacts" / "run_manifest.json",
        TEMPLATE_ROOT / "quality_contract.json": workspace / "artifacts" / "quality_contract.json",
        TEMPLATE_ROOT / "result_registry.json": workspace / "results" / "result_registry.json",
        TEMPLATE_ROOT / "literature_library.json": workspace / "literature" / "library.json",
        TEMPLATE_ROOT / "literature_claim_map.json": workspace / "literature" / "claim_map.json",
    }
    for source, destination in copies.items():
        if not destination.exists():
            shutil.copyfile(source, destination)

    # 只补 run_id/指纹；spec_checksum 等留空，Stage 2 预检会因此拒绝未填写的清单。
    stamped = {
        workspace / "state" / "artifact_manifest.json": {"run_id": run_id},
        workspace / "artifacts" / "run_manifest.json": {
            "run_id": run_id,
            "input_fingerprint": fingerprint,
        },
        workspace / "results" / "result_registry.json": {"run_id": run_id},
    }
    for path, updates in stamped.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("run_id") in (None, "", "UNINITIALIZED"):
            payload.update(updates)
            write_json(path, payload)

    return {
        "workspace": str(workspace),
        "run_id": run_id,
        "workflow": str(state_path),
        "input_fingerprint": fingerprint,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a CUMCM v2 shared workspace.")
    parser.add_argument("workspace", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--competition", default="cumcm", choices=("cumcm",))
    args = parser.parse_args()
    try:
        result = initialize(args.workspace.resolve(), args.competition)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
