#!/usr/bin/env python3
"""Revision-guarded state transitions for the CUMCM v2 two-agent workflow."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from validate_handoff import validate_handoff

SCHEMA_VERSION = "4.0"
OWNER_BY_STAGE = {0: "claude", 1: "codex", 2: "claude", 3: "codex", 4: "claude", 5: "codex", 6: "claude"}
ALLOWED_TRANSITIONS = {0: {1}, 1: {2}, 2: {3}, 3: {2, 4}, 4: {5}, 5: {4, 6}, 6: set()}
FORWARD_STAGE = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6}


class WorkflowError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def state_path(workspace: Path) -> Path:
    return workspace / "state" / "workflow.json"


def load_state(workspace: Path) -> dict[str, object]:
    path = state_path(workspace)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取工作流状态 {path}: {exc}") from exc
    if not isinstance(state, dict) or state.get("_schema_version") != SCHEMA_VERSION:
        raise WorkflowError("workflow.json 不是受支持的 v4.0 状态")
    stage = state.get("current_stage")
    revision = state.get("revision")
    if isinstance(stage, bool) or not isinstance(stage, int) or stage not in OWNER_BY_STAGE:
        raise WorkflowError("current_stage 必须是 0..6 的整数")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise WorkflowError("revision 必须是非负整数")
    return state


def atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def require_revision(state: dict[str, object], expected: int) -> None:
    actual = state["revision"]
    if actual != expected:
        raise WorkflowError(f"revision 冲突：期望 {expected}，实际 {actual}；请重新读取状态")


def require_owner(state: dict[str, object], actor: str) -> None:
    if state.get("current_owner") != actor:
        raise WorkflowError(
            f"当前 owner 是 {state.get('current_owner')}，{actor} 不得写共享状态或产物"
        )


def next_owner_for(stage: int) -> str | None:
    next_stage = FORWARD_STAGE.get(stage)
    return OWNER_BY_STAGE.get(next_stage) if next_stage is not None else None


def start(workspace: Path, actor: str, expected_revision: int) -> dict[str, object]:
    state = load_state(workspace)
    require_revision(state, expected_revision)
    require_owner(state, actor)
    if state.get("status") not in {"ready", "needs_revision"}:
        raise WorkflowError(f"状态 {state.get('status')} 不能 start")
    state["status"] = "in_progress"
    state["revision"] = expected_revision + 1
    state["updated_at"] = utc_now()
    atomic_write(state_path(workspace), state)
    return state


def resolve_workspace_path(workspace: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else workspace / path
    resolved_workspace = workspace.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_workspace and resolved_workspace not in resolved.parents:
        raise WorkflowError("handoff 必须位于共享工作区内")
    return resolved


def handoff(
    workspace: Path,
    actor: str,
    recipient: str,
    next_stage: int,
    handoff_path: Path,
    expected_revision: int,
    acceptance: str,
) -> dict[str, object]:
    state = load_state(workspace)
    require_revision(state, expected_revision)
    require_owner(state, actor)
    current_stage = int(state["current_stage"])
    if state.get("status") != "in_progress":
        raise WorkflowError("只有 in_progress 阶段可以交接")
    if next_stage not in ALLOWED_TRANSITIONS[current_stage]:
        raise WorkflowError(f"不允许从 Stage {current_stage} 转到 Stage {next_stage}")
    expected_recipient = OWNER_BY_STAGE[next_stage]
    if recipient != expected_recipient:
        raise WorkflowError(f"Stage {next_stage} 的 owner 必须是 {expected_recipient}")
    is_revision = next_stage < current_stage
    if is_revision != (acceptance == "needs_revision"):
        raise WorkflowError("回退必须使用 needs_revision，前进必须使用 passed")

    resolved_handoff = resolve_workspace_path(workspace, handoff_path)
    ok, errors, fields = validate_handoff(
        resolved_handoff,
        expected_from=actor,
        expected_to=recipient,
        expected_next_stage=next_stage,
    )
    if not ok:
        raise WorkflowError("交接单校验失败: " + "; ".join(errors))
    if fields.get("Completed Stage") != current_stage:
        raise WorkflowError("交接单 Completed Stage 与当前阶段不一致")
    if fields.get("Workflow Revision") != expected_revision:
        raise WorkflowError("交接单 Workflow Revision 与当前状态不一致")
    if fields.get("Acceptance") != acceptance:
        raise WorkflowError("交接单 Acceptance 与命令参数不一致")

    completed = [int(value) for value in state.get("completed_stages", []) if isinstance(value, int)]
    if is_revision:
        completed = [value for value in completed if value < next_stage]
    elif current_stage not in completed:
        completed.append(current_stage)
    state.update(
        current_stage=next_stage,
        current_owner=recipient,
        previous_owner=actor,
        next_owner=next_owner_for(next_stage),
        status="needs_revision" if is_revision else "ready",
        revision=expected_revision + 1,
        active_handoff=resolved_handoff.relative_to(workspace.resolve()).as_posix(),
        completed_stages=sorted(set(completed)),
        updated_at=utc_now(),
    )
    atomic_write(state_path(workspace), state)
    return state


def complete(workspace: Path, actor: str, expected_revision: int) -> dict[str, object]:
    state = load_state(workspace)
    require_revision(state, expected_revision)
    require_owner(state, actor)
    if state.get("current_stage") != 6 or state.get("status") != "in_progress":
        raise WorkflowError("只有进行中的 Stage 6 可以完成工作流")
    if not (workspace / "paper.md").is_file():
        raise WorkflowError("完成前必须存在 paper.md")
    completed = sorted(set([*state.get("completed_stages", []), 6]))
    state.update(
        current_owner="user",
        previous_owner=actor,
        next_owner=None,
        status="complete",
        revision=expected_revision + 1,
        completed_stages=completed,
        updated_at=utc_now(),
    )
    atomic_write(state_path(workspace), state)
    return state


def emit(state: dict[str, object]) -> None:
    print(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage CUMCM v2 workflow state.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--actor", choices=("claude", "codex"), required=True)
    start_parser.add_argument("--expect-revision", type=int, required=True)

    handoff_parser = subparsers.add_parser("handoff")
    handoff_parser.add_argument("--actor", choices=("claude", "codex"), required=True)
    handoff_parser.add_argument("--to", choices=("claude", "codex"), required=True)
    handoff_parser.add_argument("--next-stage", type=int, choices=range(7), required=True)
    handoff_parser.add_argument("--handoff", type=Path, required=True)
    handoff_parser.add_argument("--expect-revision", type=int, required=True)
    handoff_parser.add_argument("--acceptance", choices=("passed", "needs_revision"), required=True)

    complete_parser = subparsers.add_parser("complete")
    complete_parser.add_argument("--actor", choices=("claude", "codex"), required=True)
    complete_parser.add_argument("--expect-revision", type=int, required=True)

    args = parser.parse_args()
    workspace = args.workspace.resolve()
    try:
        if args.command == "status":
            state = load_state(workspace)
        elif args.command == "start":
            state = start(workspace, args.actor, args.expect_revision)
        elif args.command == "handoff":
            state = handoff(
                workspace,
                args.actor,
                args.to,
                args.next_stage,
                args.handoff,
                args.expect_revision,
                args.acceptance,
            )
        else:
            state = complete(workspace, args.actor, args.expect_revision)
    except (OSError, WorkflowError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    emit(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
