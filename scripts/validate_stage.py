#!/usr/bin/env python3
"""Mechanical preflight checks for the Claude-owned stages 2, 4 and 6.

Only checks that a machine can decide reliably live here: file presence,
schema shape, checksum agreement, path resolution, placeholder residue and
credential patterns. Mathematical correctness, model choice, innovation and
result plausibility stay with the Codex stage 3/5 review — they are not
verifiable here and must not be dressed up as hard gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

RUN_MANIFEST_SCHEMA = "1.0"
ARTIFACT_MANIFEST_SCHEMA = "1.0"
PATCH_PLAN_SCHEMA = "1.0"

ARTIFACT_STAGES = set(range(7))
ARTIFACT_OWNERS = {"claude", "codex"}
OWNER_BY_STAGE = {
    0: "claude",
    1: "codex",
    2: "claude",
    3: "codex",
    4: "claude",
    5: "codex",
    6: "claude",
}
ARTIFACT_STATUSES = {"draft", "verified", "needs_revision", "stale", "final"}
UNUSABLE_STATUSES = {"needs_revision", "stale"}

PATCH_SEVERITIES = {"blocker", "high", "medium", "low"}
PATCH_STATUSES = {"pending", "applied", "verified", "accepted"}
ACCEPTABLE_SEVERITIES = {"medium", "low"}
PATCH_REQUIRED_FIELDS = (
    "id",
    "target",
    "severity",
    "problem",
    "evidence",
    "action",
    "acceptance_check",
    "status",
)

SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
RUN_ID_PATTERN = re.compile(r"^[0-9A-Za-z._:-]{4,80}$")

# 只保留高置信度残留标记；XXX 之类在中文论文里可能是正常脱敏写法，不纳入。
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|TBD)\b")
# 模板占位符：<a|b> 形式的枚举槽，或含中文的 <待填> 形式。
PLACEHOLDER_PATTERNS = (
    re.compile(r"<[A-Za-z0-9_][A-Za-z0-9_./-]*(?:\|[A-Za-z0-9_./-]+)+>"),
    re.compile(r"<[0-9A-Za-z_./·、，,：: -]*[一-鿿][0-9A-Za-z_./·、，,：: 一-鿿-]*>"),
)
CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|secret[_-]?key|bearer)\b\s*[:=]\s*"
        r"[\"']?[A-Za-z0-9_\-.]{16,}"
    ),
)
FENCE_PATTERN = re.compile(r"^[ \t]*(?:```|~~~).*?$.*?^[ \t]*(?:```|~~~)[ \t]*$", re.M | re.S)
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(\S.*?)[ \t]*$", re.M)
REFERENCE_HEADING_PATTERN = re.compile(r"^#{1,6}[ \t]*(参考文献|References)\b.*$", re.M | re.I)
REFERENCE_ENTRY_PATTERN = re.compile(r"^[ \t]*(?:\[(\d{1,3})\]|(\d{1,3})[.、])\s*\S", re.M)
# 正文数字引用：排除 [1]: 链接定义、][1] 引用式链接、x[1] 下标和 [1](url) 普通链接。
CITATION_PATTERN = re.compile(r"(?<![\]A-Za-z0-9_])\[([\d,，\s-]{1,40})\](?![(:])")


class Report:
    """Errors block the transition; warnings are advisory only."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def as_dict(self, stage: int) -> dict[str, object]:
        return {
            "ok": self.ok,
            "stage": stage,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"无法读取 {path.name}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"{path.name} 不是合法 JSON: {exc}"


def read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"无法读取 {path.name}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"{path.name} 不是 UTF-8 文本: {exc}"


def resolve_inside(workspace: Path, raw: str) -> tuple[Path | None, str | None]:
    """Resolve a workspace-relative path, rejecting absolute paths and escapes."""
    text = raw.strip().strip("`")
    if not text:
        return None, "路径为空"
    candidate = Path(text)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", text):
        return None, f"必须使用工作区相对路径: {text}"
    resolved = (workspace / candidate).resolve()
    root = workspace.resolve()
    if resolved != root and root not in resolved.parents:
        return None, f"路径逃出工作区: {text}"
    return resolved, None


def strip_code(text: str) -> str:
    """Blank out fenced and inline code so prose scans stay low-noise."""
    without_fence = FENCE_PATTERN.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return INLINE_CODE_PATTERN.sub(" ", without_fence)


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_placeholders(report: Report, label: str, text: str) -> None:
    prose = strip_code(HTML_COMMENT_PATTERN.sub(" ", text))
    for match in TODO_PATTERN.finditer(prose):
        report.error(f"{label}:{line_of(prose, match.start())} 残留标记 {match.group(1)}")
    for pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(prose):
            report.error(
                f"{label}:{line_of(prose, match.start())} 残留模板占位符 {match.group(0)}"
            )


def scan_credentials(report: Report, label: str, text: str) -> None:
    # 凭据检查不剥离代码块：泄漏的 key 往往正好写在代码里。
    for pattern in CREDENTIAL_PATTERNS:
        for match in pattern.finditer(text):
            report.error(
                f"{label}:{line_of(text, match.start())} 疑似凭据模式，禁止写入交付物"
            )


def scan_images(report: Report, workspace: Path, document: Path, text: str) -> list[Path]:
    resolved_targets: list[Path] = []
    base = document.parent
    for match in IMAGE_PATTERN.finditer(text):
        raw = match.group(1).strip("<>")
        label = f"{document.name}:{line_of(text, match.start())}"
        if Path(raw).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", raw):
            report.error(f"{label} 图片必须使用相对路径: {raw}")
            continue
        if urlsplit(raw).scheme or raw.startswith("//"):
            continue
        target = unquote(raw.split("#", 1)[0])
        if not target:
            continue
        candidate = (base / Path(target)).resolve()
        root = workspace.resolve()
        if root not in candidate.parents:
            report.error(f"{label} 图片路径逃出工作区: {target}")
            continue
        if not candidate.is_file():
            report.error(f"{label} 图片路径不存在: {target}")
            continue
        resolved_targets.append(candidate)
    return resolved_targets


def scan_empty_sections(report: Report, label: str, text: str) -> None:
    body = HTML_COMMENT_PATTERN.sub(" ", text)
    headings = [
        (match.start(), match.end(), len(match.group(1)), match.group(2))
        for match in HEADING_PATTERN.finditer(body)
    ]
    for index, (_, end, level, title) in enumerate(headings):
        stop = headings[index + 1][0] if index + 1 < len(headings) else len(body)
        if body[end:stop].strip():
            continue
        has_child = index + 1 < len(headings) and headings[index + 1][2] > level
        if not has_child:
            report.error(f"{label}:{line_of(body, end)} 章节为空: {title}")


def expand_citation_group(raw: str) -> set[int] | None:
    """Expand `1`, `1,2`, `1-3` into numbers; return None when it is not a citation."""
    numbers: set[int] = set()
    for part in re.split(r"[,，]", raw):
        item = part.strip()
        if not item:
            return None
        range_match = re.fullmatch(r"(\d{1,3})\s*-\s*(\d{1,3})", item)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            if low < 1 or high < low or high - low > 60:
                return None
            numbers.update(range(low, high + 1))
            continue
        if not item.isdigit():
            return None
        value = int(item)
        if value < 1:
            # 编号从 1 开始；[0, 1] 之类是区间记号，不是引用。
            return None
        numbers.add(value)
    return numbers or None


def scan_citations(report: Report, label: str, text: str) -> None:
    """Only checks the reliably identifiable numeric citation style."""
    prose = strip_code(HTML_COMMENT_PATTERN.sub(" ", text))
    heading = REFERENCE_HEADING_PATTERN.search(prose)
    body = prose[: heading.start()] if heading else prose
    references = prose[heading.end():] if heading else ""
    defined = {
        int(match.group(1) or match.group(2))
        for match in REFERENCE_ENTRY_PATTERN.finditer(references)
    }

    cited: dict[int, int] = {}
    for match in CITATION_PATTERN.finditer(body):
        numbers = expand_citation_group(match.group(1))
        if not numbers:
            continue
        for number in numbers:
            cited.setdefault(number, line_of(body, match.start()))

    if not cited:
        if not heading:
            report.warn(f"{label} 未发现可识别的数字引用与参考文献章节，需人工确认引用体例")
        elif not defined:
            report.error(f"{label} 参考文献章节没有可识别的编号条目")
        else:
            report.warn(f"{label} 参考文献有条目但正文未发现可识别的数字引用标注")
        return
    if not heading:
        report.error(f"{label} 正文有数字引用但缺少参考文献章节")
        return
    if not defined:
        report.error(f"{label} 参考文献章节没有可识别的编号条目")
        return
    for number in sorted(set(cited) - defined):
        report.error(f"{label}:{cited[number]} 引用 [{number}] 在参考文献中不存在")
    for number in sorted(defined - set(cited)):
        report.warn(f"{label} 参考文献 [{number}] 未被正文引用")


def require_files(report: Report, workspace: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        path = workspace / relative
        if not path.is_file():
            report.error(f"缺少必需产物: {relative}")
        elif not path.read_bytes().strip():
            report.error(f"必需产物为空: {relative}")


def check_declared_path(
    report: Report,
    workspace: Path,
    raw: object,
    context: str,
) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        report.error(f"{context} 路径必须是非空字符串")
        return None
    resolved, error = resolve_inside(workspace, raw)
    if error:
        report.error(f"{context} {error}")
        return None
    assert resolved is not None
    if not resolved.is_file():
        report.error(f"{context} 声明的文件不存在: {raw}")
        return None
    if not resolved.read_bytes().strip():
        report.error(f"{context} 声明的文件为空: {raw}")
        return None
    return resolved


def validate_run_manifest(
    report: Report,
    workspace: Path,
    state: dict[str, object] | None,
) -> set[Path]:
    declared: set[Path] = set()
    path = workspace / "artifacts" / "run_manifest.json"
    if not path.is_file():
        report.error("缺少 artifacts/run_manifest.json；Stage 2 必须记录可复现运行清单")
        return declared
    data, error = load_json(path)
    if error:
        report.error(error)
        return declared
    if not isinstance(data, dict):
        report.error("run_manifest.json 顶层必须是对象")
        return declared
    if data.get("_schema_version") != RUN_MANIFEST_SCHEMA:
        report.error(f"run_manifest.json 的 _schema_version 必须是 {RUN_MANIFEST_SCHEMA}")

    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        report.error("run_manifest.json 缺少合法 run_id")
    elif state is not None and state.get("run_id") not in (None, run_id):
        report.error(
            f"run_manifest.json 的 run_id {run_id} 与 workflow.json 的 {state.get('run_id')} 不一致"
        )

    fingerprint = data.get("input_fingerprint")
    if not isinstance(fingerprint, str) or not SHA256_PATTERN.fullmatch(fingerprint):
        report.error("run_manifest.json 的 input_fingerprint 必须是 sha256:<64 位十六进制>")
    elif state is not None and isinstance(state.get("input_fingerprint"), str):
        if state["input_fingerprint"] != fingerprint:
            report.error("run_manifest.json 的 input_fingerprint 与 workflow.json 不一致")

    checksum = data.get("spec_checksum")
    if not isinstance(checksum, str) or not SHA256_PATTERN.fullmatch(checksum):
        report.error("run_manifest.json 的 spec_checksum 必须是 sha256:<64 位十六进制>")
    else:
        spec = workspace / "artifacts" / "model_spec.md"
        if spec.is_file() and sha256_file(spec) != checksum:
            report.error(
                "spec_checksum 与 artifacts/model_spec.md 当前内容不一致；"
                "规格已变化时必须重新运行并更新清单"
            )
    if not isinstance(data.get("environment"), str) or not data["environment"].strip():
        report.error("run_manifest.json 必须记录 environment（解释器与关键依赖版本）")
    declared.update(validate_run_manifest_subproblems(report, workspace, data.get("subproblems")))
    deviations = data.get("model_deviations")
    if deviations is not None:
        check_declared_path(report, workspace, deviations, "run_manifest.model_deviations")
    return declared


def validate_run_manifest_subproblems(
    report: Report,
    workspace: Path,
    subproblems: object,
) -> set[Path]:
    declared: set[Path] = set()
    if not isinstance(subproblems, list) or not subproblems:
        report.error("run_manifest.json 的 subproblems 必须是非空数组")
        return declared
    seen: set[str] = set()
    for index, entry in enumerate(subproblems):
        context = f"run_manifest.subproblems[{index}]"
        if not isinstance(entry, dict):
            report.error(f"{context} 必须是对象")
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            report.error(f"{context} 缺少非空 id")
        elif identifier in seen:
            report.error(f"{context} 子问题 id 重复: {identifier}")
        else:
            seen.add(identifier)
        label = identifier if isinstance(identifier, str) and identifier.strip() else context
        for field in ("command", "seed"):
            if field not in entry:
                report.error(f"子问题 {label} 缺少字段 {field}")
        if "command" in entry and not (
            isinstance(entry["command"], str) and entry["command"].strip()
        ):
            report.error(f"子问题 {label} 的 command 必须是非空字符串")
        for field in ("code", "results", "figures"):
            values = entry.get(field)
            if not isinstance(values, list) or not values:
                report.error(f"子问题 {label} 的 {field} 必须是非空数组")
                continue
            for item in values:
                resolved = check_declared_path(report, workspace, item, f"子问题 {label} 的 {field}")
                if resolved is not None:
                    declared.add(resolved)
    return declared


def validate_artifact_manifest(
    report: Report,
    workspace: Path,
    state: dict[str, object] | None,
) -> dict[Path, dict[str, object]]:
    path = workspace / "state" / "artifact_manifest.json"
    registry: dict[Path, dict[str, object]] = {}
    if not path.is_file():
        report.error("缺少 state/artifact_manifest.json")
        return registry
    data, error = load_json(path)
    if error:
        report.error(error)
        return registry
    if not isinstance(data, dict):
        report.error("artifact_manifest.json 顶层必须是对象")
        return registry
    if data.get("_schema_version") != ARTIFACT_MANIFEST_SCHEMA:
        report.error(
            f"artifact_manifest.json 的 _schema_version 必须是 {ARTIFACT_MANIFEST_SCHEMA}"
        )
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        report.error("artifact_manifest.json 缺少合法 run_id")
    elif state is not None and state.get("run_id") not in (None, run_id):
        report.error("artifact_manifest.json 的 run_id 与 workflow.json 不一致")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        report.error("artifact_manifest.json 的 artifacts 必须是数组")
        return registry
    for index, entry in enumerate(artifacts):
        resolved = validate_artifact_entry(report, workspace, index, entry, registry)
        if resolved is not None and isinstance(entry, dict):
            registry[resolved] = entry
    return registry


def validate_artifact_entry(
    report: Report,
    workspace: Path,
    index: int,
    entry: object,
    registry: dict[Path, dict[str, object]],
) -> Path | None:
    context = f"artifact_manifest.artifacts[{index}]"
    if not isinstance(entry, dict):
        report.error(f"{context} 必须是对象")
        return None
    missing = [
        field
        for field in ("path", "stage", "owner", "status", "sha256", "inputs")
        if field not in entry
    ]
    if missing:
        report.error(f"{context} 缺少字段: {', '.join(missing)}")

    stage = entry.get("stage")
    if isinstance(stage, bool) or not isinstance(stage, int) or stage not in ARTIFACT_STAGES:
        report.error(f"{context} stage 必须是 0..6 的整数")
    owner = entry.get("owner")
    if owner not in ARTIFACT_OWNERS:
        report.error(f"{context} owner 必须是 claude 或 codex")
    elif isinstance(stage, int) and stage in OWNER_BY_STAGE and owner != OWNER_BY_STAGE[stage]:
        report.error(f"{context} Stage {stage} 的 owner 必须是 {OWNER_BY_STAGE[stage]}")
    status = entry.get("status")
    if status not in ARTIFACT_STATUSES:
        report.error(
            f"{context} status 必须属于 {', '.join(sorted(ARTIFACT_STATUSES))}"
        )
    inputs = entry.get("inputs")
    if not isinstance(inputs, list):
        report.error(f"{context} inputs 必须是数组（可为空）")
    else:
        for input_index, raw_input in enumerate(inputs):
            input_context = f"{context}.inputs[{input_index}]"
            if not isinstance(raw_input, str) or not raw_input.strip():
                report.error(f"{input_context} 必须是非空字符串")
                continue
            input_path, input_error = resolve_inside(workspace, raw_input)
            if input_error:
                report.error(f"{input_context} {input_error}")
            elif input_path is not None and not input_path.exists():
                report.error(f"{input_context} 声明的输入不存在: {raw_input}")

    resolved = check_declared_path(report, workspace, entry.get("path"), context)
    if resolved is None:
        return None
    if resolved in registry:
        report.error(f"{context} path 重复登记: {entry.get('path')}")
        return None
    checksum = entry.get("sha256")
    if not isinstance(checksum, str) or not SHA256_PATTERN.fullmatch(checksum):
        report.error(f"{context} sha256 必须是 sha256:<64 位十六进制>")
    elif sha256_file(resolved) != checksum:
        report.error(f"{context} sha256 与文件当前内容不一致: {entry.get('path')}")
    return resolved


def validate_stage_2_registry(
    report: Report,
    workspace: Path,
    declared: set[Path],
    registry: dict[Path, dict[str, object]],
) -> None:
    for path in sorted(declared, key=str):
        relative = path.relative_to(workspace.resolve()).as_posix()
        entry = registry.get(path)
        if entry is None:
            report.error(f"run_manifest 声明的 Stage 2 产物未登记到 artifact manifest: {relative}")
            continue
        if entry.get("stage") != 2:
            report.error(f"run_manifest 声明的产物 {relative} 在 artifact manifest 中 stage 必须是 2")
        if entry.get("owner") != "claude":
            report.error(f"run_manifest 声明的产物 {relative} 在 artifact manifest 中 owner 必须是 claude")
        if entry.get("status") in UNUSABLE_STATUSES:
            report.error(
                f"run_manifest 声明的产物 {relative} 状态为 {entry.get('status')}，不得进入 Stage 3"
            )


def validate_patch_plan(report: Report, workspace: Path) -> None:
    path = workspace / "reviews" / "final_patch_plan.json"
    if not path.is_file():
        report.error("缺少 reviews/final_patch_plan.json；Stage 6 必须依据 Codex 修改单执行")
        return
    data, error = load_json(path)
    if error:
        report.error(error)
        return
    if not isinstance(data, dict):
        report.error("final_patch_plan.json 顶层必须是对象")
        return
    if data.get("_schema_version") != PATCH_PLAN_SCHEMA:
        report.error(f"final_patch_plan.json 的 _schema_version 必须是 {PATCH_PLAN_SCHEMA}")
    if (data.get("verdict"), data.get("target_stage")) != ("passed", 6):
        report.error(
            "Stage 6 只接受 verdict=passed 且 target_stage=6 的修改单；"
            "needs_revision 应回到 Stage 4"
        )
    patches = data.get("patches")
    if not isinstance(patches, list):
        report.error("final_patch_plan.json 的 patches 必须是数组")
        return
    seen: set[str] = set()
    for index, entry in enumerate(patches):
        validate_patch_item(report, workspace, index, entry, seen)


def validate_patch_item(
    report: Report,
    workspace: Path,
    index: int,
    entry: object,
    seen: set[str],
) -> None:
    context = f"final_patch_plan.patches[{index}]"
    if not isinstance(entry, dict):
        report.error(f"{context} 必须是对象")
        return
    missing = [field for field in PATCH_REQUIRED_FIELDS if field not in entry]
    if missing:
        report.error(f"{context} 缺少字段: {', '.join(missing)}")
    identifier = entry.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        report.error(f"{context} 缺少非空 id")
    elif identifier in seen:
        report.error(f"{context} id 重复: {identifier}")
    else:
        seen.add(identifier)
    label = identifier if isinstance(identifier, str) and identifier.strip() else context

    target = entry.get("target")
    if not isinstance(target, dict):
        report.error(f"{label} 的 target 必须是对象，含 file 与 anchor")
    else:
        for field in ("file", "anchor"):
            value = target.get(field)
            if not isinstance(value, str) or not value.strip():
                report.error(f"{label} 的 target.{field} 必须是非空字符串")
        if isinstance(target.get("file"), str) and target["file"].strip():
            check_declared_path(report, workspace, target["file"], f"{label} 的 target.file")

    for field in ("problem", "evidence", "action", "acceptance_check"):
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            report.error(f"{label} 的 {field} 必须是非空字符串")

    severity = entry.get("severity")
    if severity not in PATCH_SEVERITIES:
        report.error(f"{label} 的 severity 必须属于 {', '.join(sorted(PATCH_SEVERITIES))}")
    status = entry.get("status")
    if status not in PATCH_STATUSES:
        report.error(f"{label} 的 status 必须属于 {', '.join(sorted(PATCH_STATUSES))}")
        return
    if status == "pending":
        report.error(f"{label} 仍是 pending；完成前必须 applied、verified 或 accepted")
        return
    if status != "accepted":
        return
    if severity in PATCH_SEVERITIES - ACCEPTABLE_SEVERITIES:
        report.error(f"{label} 是 {severity} 项，不得用 accepted 跳过，必须实际修改")
    note = entry.get("resolution_note")
    if not isinstance(note, str) or len(note.strip()) < 8:
        report.error(f"{label} 使用 accepted 时必须在 resolution_note 写明接受理由")


def read_state(workspace: Path) -> dict[str, object] | None:
    data, _ = load_json(workspace / "state" / "workflow.json")
    return data if isinstance(data, dict) else None


def flag_unusable_figures(
    report: Report,
    workspace: Path,
    registry: dict[Path, dict[str, object]],
    figures: list[Path],
) -> None:
    for figure in figures:
        entry = registry.get(figure)
        if entry and entry.get("status") in UNUSABLE_STATUSES:
            relative = figure.relative_to(workspace.resolve()).as_posix()
            report.error(
                f"论文引用了状态为 {entry['status']} 的图: {relative}；"
                "必须先重做并更新 manifest"
            )


def validate_stage_2(workspace: Path) -> Report:
    report = Report()
    state = read_state(workspace)
    require_files(
        report,
        workspace,
        (
            "artifacts/model_spec.md",
            "artifacts/implementation_contract.md",
            "artifacts/model_deviations.md",
        ),
    )
    declared = validate_run_manifest(report, workspace, state)
    registry = validate_artifact_manifest(report, workspace, state)
    validate_stage_2_registry(report, workspace, declared, registry)
    return report


def validate_stage_4(workspace: Path) -> Report:
    report = Report()
    state = read_state(workspace)
    require_files(report, workspace, ("paper_draft.md", "support_materials_manifest.md"))
    sections = sorted((workspace / "paper_workspace").glob("*.md"))
    if not sections:
        report.error("paper_workspace/ 中没有章节文件；Stage 4 必须留下可追溯的分章产物")

    draft = workspace / "paper_draft.md"
    if draft.is_file():
        text, error = read_text(draft)
        if error:
            report.error(error)
        else:
            assert text is not None
            scan_placeholders(report, draft.name, text)
            scan_credentials(report, draft.name, text)
            scan_empty_sections(report, draft.name, text)
            scan_citations(report, draft.name, text)
            figures = scan_images(report, workspace, draft, text)
            # Stage 4 只借 manifest 判断图状态，manifest 本身的完整性归 Stage 2/6 检查。
            registry = validate_artifact_manifest(Report(), workspace, state)
            flag_unusable_figures(report, workspace, registry, figures)
    for section in sections:
        text, error = read_text(section)
        if error:
            report.error(error)
            continue
        assert text is not None
        label = f"paper_workspace/{section.name}"
        scan_placeholders(report, label, text)
        scan_credentials(report, label, text)
    return report


def validate_stage_6(workspace: Path) -> Report:
    report = Report()
    state = read_state(workspace)
    require_files(report, workspace, ("paper.md",))
    validate_patch_plan(report, workspace)
    registry = validate_artifact_manifest(report, workspace, state)

    paper = workspace / "paper.md"
    if not paper.is_file():
        return report
    text, error = read_text(paper)
    if error:
        report.error(error)
        return report
    assert text is not None
    scan_placeholders(report, paper.name, text)
    scan_credentials(report, paper.name, text)
    scan_empty_sections(report, paper.name, text)
    scan_citations(report, paper.name, text)
    figures = scan_images(report, workspace, paper, text)
    flag_unusable_figures(report, workspace, registry, figures)

    entry = registry.get(paper.resolve())
    if entry is None:
        report.error("paper.md 未登记到 state/artifact_manifest.json")
    elif entry.get("status") != "final":
        report.error(f"paper.md 在 artifact manifest 中的状态是 {entry.get('status')}，应为 final")
    return report


VALIDATORS = {2: validate_stage_2, 4: validate_stage_4, 6: validate_stage_6}


def validate_stage(workspace: Path, stage: int) -> Report:
    if stage not in VALIDATORS:
        raise ValueError(f"Stage {stage} 没有程序化预检；只支持 {sorted(VALIDATORS)}")
    return VALIDATORS[stage](workspace.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the mechanical preflight for a Claude-owned stage."
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--stage", type=int, choices=sorted(VALIDATORS), required=True)
    args = parser.parse_args()
    report = validate_stage(args.workspace, args.stage)
    print(json.dumps(report.as_dict(args.stage), ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
