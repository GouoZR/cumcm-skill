#!/usr/bin/env python3
"""Validate the fixed Markdown handoff contract used by the v2 workflow."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FIELD_PATTERN = re.compile(r"^- ([A-Za-z ]+):\s*(.+?)\s*$", re.MULTILINE)
REQUIRED_FIELDS = {
    "From",
    "To",
    "Completed Stage",
    "Next Stage",
    "Workflow Revision",
    "Acceptance",
}
REQUIRED_HEADINGS = (
    "已完成内容",
    "新增或修改文件",
    "已执行验证",
    "已冻结事实与决策",
    "未解决问题",
    "下一位 Agent 的明确任务",
    "禁止修改的文件",
    "验收说明",
)
ACTORS = {"claude", "codex"}
ACCEPTANCE = {"passed", "needs_revision"}


def validate_handoff(
    path: Path,
    expected_from: str | None = None,
    expected_to: str | None = None,
    expected_next_stage: int | None = None,
) -> tuple[bool, list[str], dict[str, object]]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [str(exc)], {}

    fields = {key: value.strip("`<>") for key, value in FIELD_PATTERN.findall(text)}
    missing_fields = sorted(REQUIRED_FIELDS - fields.keys())
    if missing_fields:
        errors.append("缺少字段: " + ", ".join(missing_fields))

    for heading in REQUIRED_HEADINGS:
        if not re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE):
            errors.append(f"缺少章节: {heading}")

    from_actor = fields.get("From")
    to_actor = fields.get("To")
    if from_actor and from_actor not in ACTORS:
        errors.append(f"非法 From: {from_actor}")
    if to_actor and to_actor not in ACTORS:
        errors.append(f"非法 To: {to_actor}")
    if from_actor and to_actor and from_actor == to_actor:
        errors.append("From 与 To 不得相同")
    if expected_from and from_actor != expected_from:
        errors.append(f"From 应为 {expected_from}，实际为 {from_actor}")
    if expected_to and to_actor != expected_to:
        errors.append(f"To 应为 {expected_to}，实际为 {to_actor}")

    parsed: dict[str, object] = dict(fields)
    for key in ("Completed Stage", "Next Stage", "Workflow Revision"):
        if key in fields:
            try:
                parsed[key] = int(fields[key])
            except ValueError:
                errors.append(f"{key} 必须是整数")
    for key in ("Completed Stage", "Next Stage"):
        value = parsed.get(key)
        if isinstance(value, int) and not 0 <= value <= 6:
            errors.append(f"{key} 必须位于 0..6")
    revision = parsed.get("Workflow Revision")
    if isinstance(revision, int) and revision < 0:
        errors.append("Workflow Revision 不得为负数")
    if expected_next_stage is not None and parsed.get("Next Stage") != expected_next_stage:
        errors.append(
            f"Next Stage 应为 {expected_next_stage}，实际为 {parsed.get('Next Stage')}"
        )
    acceptance = fields.get("Acceptance")
    if acceptance and acceptance not in ACCEPTANCE:
        errors.append(f"非法 Acceptance: {acceptance}")

    return not errors, errors, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CUMCM handoff Markdown file.")
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--from", dest="expected_from", choices=sorted(ACTORS))
    parser.add_argument("--to", dest="expected_to", choices=sorted(ACTORS))
    parser.add_argument("--next-stage", type=int, choices=range(7))
    args = parser.parse_args()
    ok, errors, fields = validate_handoff(
        args.handoff,
        expected_from=args.expected_from,
        expected_to=args.expected_to,
        expected_next_stage=args.next_stage,
    )
    print(json.dumps({"ok": ok, "errors": errors, "fields": fields}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
