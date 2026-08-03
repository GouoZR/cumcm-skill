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

# 允许显式写“无”的章节；其余章节必须有实质内容。
NULLABLE_HEADINGS = {"已冻结事实与决策", "未解决问题", "禁止修改的文件"}
SUBSTANTIVE_HEADINGS = tuple(
    heading for heading in REQUIRED_HEADINGS if heading not in NULLABLE_HEADINGS
)
CLAUDE_TRACE_HEADING = "SubAgent 并行产出轨迹"
CLAUDE_TRACE_STAGES = {2, 4}
TRACE_FIELDS = (
    "Partitions",
    "Main-agent verification",
    "Rejected or reworked output",
    "Fallback mode",
)
FALLBACK_MODES = {"none", "serial-main-agent", "not-applicable"}
EMPTY_MARKERS = {"无", "n/a", "na", "none", "-", "—", "待填", "tbd"}
PLACEHOLDER_LINE = re.compile(r"^<[^>]*>$")
BULLET_PREFIX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*")


def _section_bodies(text: str) -> dict[str, str]:
    """Map each level-2 heading to its raw body text."""
    matches = list(re.finditer(r"^##[ \t]+(\S.*?)[ \t]*$", text, re.MULTILINE))
    bodies: dict[str, str] = {}
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        bodies[match.group(1).strip()] = text[match.end():stop]
    return bodies


def _meaningful_items(body: str) -> list[str]:
    """Bullet/numbered items that are neither empty nor an unfilled placeholder."""
    items: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        content = BULLET_PREFIX.sub("", line).strip()
        stripped = content.strip("`").strip()
        if not stripped or PLACEHOLDER_LINE.fullmatch(stripped):
            continue
        # `<路径>`：<用途> 这类整行仍是模板的条目不算已填写。
        if re.fullmatch(r"<[^>]*>(?:\s*[：:]\s*<[^>]*>)?", stripped):
            continue
        items.append(stripped)
    return items


def _check_substance(errors: list[str], bodies: dict[str, str]) -> None:
    for heading in SUBSTANTIVE_HEADINGS:
        if heading not in bodies:
            continue
        items = _meaningful_items(bodies[heading])
        if not items:
            errors.append(f"章节未填写: {heading}")
            continue
        if all(item.strip("`").strip().lower() in EMPTY_MARKERS for item in items):
            errors.append(f"章节不得为空占位: {heading}")


def _check_claude_trace(errors: list[str], bodies: dict[str, str]) -> None:
    heading = next((name for name in bodies if name.startswith(CLAUDE_TRACE_HEADING)), None)
    if heading is None:
        errors.append(f"Stage 2/4 交接单必须包含章节: {CLAUDE_TRACE_HEADING}")
        return
    found = {
        match.group(1).strip(): match.group(2).strip().strip("`").strip()
        for match in re.finditer(
            r"^-[ \t]+([A-Za-z][A-Za-z -]*?):[ \t]*(.*?)[ \t]*$", bodies[heading], re.MULTILINE
        )
    }
    for field in TRACE_FIELDS:
        value = found.get(field)
        if value is None:
            errors.append(f"SubAgent 轨迹缺少字段: {field}")
            continue
        if not value or PLACEHOLDER_LINE.fullmatch(value):
            errors.append(f"SubAgent 轨迹未填写: {field}")

    fallback = found.get("Fallback mode", "")
    if fallback and not PLACEHOLDER_LINE.fullmatch(fallback):
        if fallback not in FALLBACK_MODES:
            errors.append(
                f"非法 Fallback mode: {fallback}；只允许 {', '.join(sorted(FALLBACK_MODES))}"
            )
        partitions = found.get("Partitions", "")
        if fallback == "none" and partitions.lower() in EMPTY_MARKERS:
            errors.append("Fallback mode 为 none 时必须列出实际分区")
    verification = found.get("Main-agent verification", "")
    if verification and verification.lower() in EMPTY_MARKERS:
        errors.append("Stage 2/4 必须记录主 Agent 核验内容，不得写“无”")


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

    bodies = _section_bodies(text)
    _check_substance(errors, bodies)
    if parsed.get("Completed Stage") in CLAUDE_TRACE_STAGES and from_actor == "claude":
        _check_claude_trace(errors, bodies)

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
