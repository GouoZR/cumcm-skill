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
QUALITY_CONTRACT_SCHEMA = "1.0"
RESULT_REGISTRY_SCHEMA = "1.0"
QUALITY_CONTRACT_FEATURE = "1.0"

QUALITY_PROBLEM_TYPES = {
    "data_processing",
    "prediction",
    "classification",
    "evaluation",
    "optimization",
    "simulation",
    "mechanism",
    "decision",
    "other",
}
RESULT_ROLES = {
    "primary",
    "baseline",
    "validation",
    "sensitivity",
    "constraint",
    "intermediate",
}
RESULT_DIRECTIONS = {"maximize", "minimize", "target", "none"}

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
    if quality_contract_enabled(state):
        quality_checksum = data.get("quality_contract_checksum")
        if not isinstance(quality_checksum, str) or not SHA256_PATTERN.fullmatch(quality_checksum):
            report.error(
                "run_manifest.json 的 quality_contract_checksum 必须是 sha256:<64 位十六进制>"
            )
        else:
            quality_path = workspace / "artifacts" / "quality_contract.json"
            if quality_path.is_file() and sha256_file(quality_path) != quality_checksum:
                report.error(
                    "quality_contract_checksum 与 artifacts/quality_contract.json 当前内容不一致；"
                    "质量契约变化后必须重新运行并更新清单"
                )
        result_registry = data.get("result_registry")
        if result_registry != "results/result_registry.json":
            report.error(
                "run_manifest.json 的 result_registry 必须指向 results/result_registry.json"
            )
        else:
            check_declared_path(
                report,
                workspace,
                result_registry,
                "run_manifest.result_registry",
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



def quality_contract_enabled(state: dict[str, object] | None) -> bool:
    """Only new workspaces opt into the v2.1 hard gates; legacy v2.0 workspaces remain usable."""
    return bool(state and state.get("quality_contract_version") == QUALITY_CONTRACT_FEATURE)


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_list(
    report: Report,
    value: object,
    context: str,
    *,
    allow_empty: bool = False,
) -> None:
    if not isinstance(value, list) or (not value and not allow_empty):
        suffix = "数组" if allow_empty else "非空数组"
        report.error(f"{context} 必须是{suffix}")
        return
    for index, item in enumerate(value):
        if not nonempty_string(item):
            report.error(f"{context}[{index}] 必须是非空字符串")


def validate_quality_contract(report: Report, workspace: Path) -> set[str]:
    path = workspace / "artifacts" / "quality_contract.json"
    identifiers: set[str] = set()
    if not path.is_file():
        report.error(
            "缺少 artifacts/quality_contract.json；Stage 1 必须固定逐问语义、验证义务和结论边界"
        )
        return identifiers
    data, error = load_json(path)
    if error:
        report.error(error)
        return identifiers
    if not isinstance(data, dict):
        report.error("quality_contract.json 顶层必须是对象")
        return identifiers
    if data.get("_schema_version") != QUALITY_CONTRACT_SCHEMA:
        report.error(
            f"quality_contract.json 的 _schema_version 必须是 {QUALITY_CONTRACT_SCHEMA}"
        )
    subproblems = data.get("subproblems")
    if not isinstance(subproblems, list) or not subproblems:
        report.error("quality_contract.json 的 subproblems 必须是非空数组")
        return identifiers
    required = (
        "id",
        "problem_type",
        "question_target",
        "analysis_unit",
        "output_definition",
        "metric_definition",
        "aggregation_scope",
        "constraints",
        "invariants",
        "baseline_or_oracle",
        "fidelity_and_discretization",
        "claim_boundaries",
    )
    for index, entry in enumerate(subproblems):
        context = f"quality_contract.subproblems[{index}]"
        if not isinstance(entry, dict):
            report.error(f"{context} 必须是对象")
            continue
        missing = [field for field in required if field not in entry]
        if missing:
            report.error(f"{context} 缺少字段: {', '.join(missing)}")
        identifier = entry.get("id")
        if not nonempty_string(identifier):
            report.error(f"{context} 缺少非空 id")
            label = context
        else:
            assert isinstance(identifier, str)
            label = identifier
            if identifier in identifiers:
                report.error(f"quality_contract 子问题 id 重复: {identifier}")
            identifiers.add(identifier)
        problem_type = entry.get("problem_type")
        if problem_type not in QUALITY_PROBLEM_TYPES:
            report.error(
                f"{label} 的 problem_type 必须属于 {', '.join(sorted(QUALITY_PROBLEM_TYPES))}"
            )
        for field in (
            "question_target",
            "analysis_unit",
            "output_definition",
            "metric_definition",
            "aggregation_scope",
            "baseline_or_oracle",
        ):
            if not nonempty_string(entry.get(field)):
                report.error(f"{label} 的 {field} 必须是非空字符串")
        for field in ("constraints", "fidelity_and_discretization", "claim_boundaries"):
            validate_string_list(report, entry.get(field), f"{label} 的 {field}")
        invariants = entry.get("invariants")
        if not isinstance(invariants, list) or not invariants:
            report.error(f"{label} 的 invariants 必须是非空数组")
            continue
        invariant_ids: set[str] = set()
        for inv_index, invariant in enumerate(invariants):
            inv_context = f"{label}.invariants[{inv_index}]"
            if not isinstance(invariant, dict):
                report.error(f"{inv_context} 必须是对象")
                continue
            for field in ("id", "statement", "check", "expected"):
                if not nonempty_string(invariant.get(field)):
                    report.error(f"{inv_context}.{field} 必须是非空字符串")
            inv_id = invariant.get("id")
            if nonempty_string(inv_id):
                assert isinstance(inv_id, str)
                if inv_id in invariant_ids:
                    report.error(f"{label} 的不变量 id 重复: {inv_id}")
                invariant_ids.add(inv_id)
    return identifiers


def validate_result_registry(
    report: Report,
    workspace: Path,
    state: dict[str, object] | None,
    expected_subproblems: set[str] | None = None,
) -> set[Path]:
    path = workspace / "results" / "result_registry.json"
    declared: set[Path] = set()
    if not path.is_file():
        report.error(
            "缺少 results/result_registry.json；核心数字必须有唯一、可定位的结果索引"
        )
        return declared
    data, error = load_json(path)
    if error:
        report.error(error)
        return declared
    if not isinstance(data, dict):
        report.error("result_registry.json 顶层必须是对象")
        return declared
    if data.get("_schema_version") != RESULT_REGISTRY_SCHEMA:
        report.error(
            f"result_registry.json 的 _schema_version 必须是 {RESULT_REGISTRY_SCHEMA}"
        )
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        report.error("result_registry.json 缺少合法 run_id")
    elif state is not None and state.get("run_id") not in (None, run_id):
        report.error("result_registry.json 的 run_id 与 workflow.json 不一致")
    if not nonempty_string(data.get("result_version")):
        report.error("result_registry.json 必须记录非空 result_version")
    metrics = data.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        report.error("result_registry.json 的 metrics 必须是非空数组")
        return declared
    required = (
        "id",
        "subproblem",
        "role",
        "name",
        "value",
        "unit",
        "direction",
        "scope",
        "source",
        "source_locator",
        "method",
        "seed",
        "evidence",
    )
    metric_ids: set[str] = set()
    primary_by_subproblem: set[str] = set()
    for index, entry in enumerate(metrics):
        context = f"result_registry.metrics[{index}]"
        if not isinstance(entry, dict):
            report.error(f"{context} 必须是对象")
            continue
        missing = [field for field in required if field not in entry]
        if missing:
            report.error(f"{context} 缺少字段: {', '.join(missing)}")
        identifier = entry.get("id")
        if not nonempty_string(identifier):
            report.error(f"{context} 缺少非空 id")
            label = context
        else:
            assert isinstance(identifier, str)
            label = identifier
            if identifier in metric_ids:
                report.error(f"result_registry 指标 id 重复: {identifier}")
            metric_ids.add(identifier)
        subproblem = entry.get("subproblem")
        if not nonempty_string(subproblem):
            report.error(f"{label} 的 subproblem 必须是非空字符串")
        elif expected_subproblems is not None and subproblem not in expected_subproblems:
            report.error(f"{label} 引用了 quality_contract 中不存在的子问题: {subproblem}")
        role = entry.get("role")
        if role not in RESULT_ROLES:
            report.error(f"{label} 的 role 必须属于 {', '.join(sorted(RESULT_ROLES))}")
        elif role == "primary" and isinstance(subproblem, str):
            primary_by_subproblem.add(subproblem)
        direction = entry.get("direction")
        if direction not in RESULT_DIRECTIONS:
            report.error(
                f"{label} 的 direction 必须属于 {', '.join(sorted(RESULT_DIRECTIONS))}"
            )
        if entry.get("value") is None:
            report.error(f"{label} 的 value 不得为 null")
        for field in ("name", "unit", "scope", "source_locator", "method"):
            if not nonempty_string(entry.get(field)):
                report.error(f"{label} 的 {field} 必须是非空字符串")
        source = check_declared_path(report, workspace, entry.get("source"), f"{label} 的 source")
        if source is not None:
            declared.add(source)
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            report.error(f"{label} 的 evidence 必须是非空数组")
        else:
            for evidence_index, raw in enumerate(evidence):
                resolved = check_declared_path(
                    report,
                    workspace,
                    raw,
                    f"{label} 的 evidence[{evidence_index}]",
                )
                if resolved is not None:
                    declared.add(resolved)
        seed = entry.get("seed")
        valid_seed = seed is None or (
            isinstance(seed, int) and not isinstance(seed, bool)
        ) or (
            isinstance(seed, list)
            and bool(seed)
            and all(isinstance(item, int) and not isinstance(item, bool) for item in seed)
        )
        if not valid_seed:
            report.error(f"{label} 的 seed 必须是 null、整数或非空整数数组")
    if expected_subproblems is not None:
        missing_primary = sorted(expected_subproblems - primary_by_subproblem)
        if missing_primary:
            report.error(
                "result_registry 每个子问题至少需要一个 primary 指标；缺少: "
                + ", ".join(missing_primary)
            )
    return declared


def run_manifest_subproblem_ids(workspace: Path) -> set[str]:
    data, _ = load_json(workspace / "artifacts" / "run_manifest.json")
    if not isinstance(data, dict) or not isinstance(data.get("subproblems"), list):
        return set()
    return {
        entry["id"]
        for entry in data["subproblems"]
        if isinstance(entry, dict) and nonempty_string(entry.get("id"))
    }


def validate_quality_artifact_registry(
    report: Report,
    workspace: Path,
    registry: dict[Path, dict[str, object]],
) -> None:
    expected = (
        ("artifacts/quality_contract.json", 1, "codex"),
        ("results/result_registry.json", 2, "claude"),
    )
    for relative, stage, owner in expected:
        path = (workspace / relative).resolve()
        entry = registry.get(path)
        if entry is None:
            report.error(f"质量门产物未登记到 artifact manifest: {relative}")
            continue
        if entry.get("stage") != stage:
            report.error(f"{relative} 在 artifact manifest 中 stage 必须是 {stage}")
        if entry.get("owner") != owner:
            report.error(f"{relative} 在 artifact manifest 中 owner 必须是 {owner}")
        if entry.get("status") in UNUSABLE_STATUSES:
            report.error(f"{relative} 状态为 {entry.get('status')}，不得继续流转")

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
    required = [
        "artifacts/model_spec.md",
        "artifacts/implementation_contract.md",
        "artifacts/model_deviations.md",
    ]
    if quality_contract_enabled(state):
        required.extend((
            "artifacts/quality_contract.json",
            "results/result_registry.json",
        ))
    require_files(report, workspace, tuple(required))
    quality_ids: set[str] | None = None
    if quality_contract_enabled(state):
        quality_ids = validate_quality_contract(report, workspace)
    declared = validate_run_manifest(report, workspace, state)
    if quality_contract_enabled(state):
        result_declared = validate_result_registry(report, workspace, state, quality_ids)
        declared.update(result_declared)
        manifest_ids = run_manifest_subproblem_ids(workspace)
        if quality_ids is not None and manifest_ids != quality_ids:
            report.error(
                "quality_contract 与 run_manifest 的子问题 id 必须完全一致；"
                f"quality={sorted(quality_ids)}, run_manifest={sorted(manifest_ids)}"
            )
    registry = validate_artifact_manifest(report, workspace, state)
    validate_stage_2_registry(report, workspace, declared, registry)
    if quality_contract_enabled(state):
        validate_quality_artifact_registry(report, workspace, registry)
    return report


def validate_stage_4(workspace: Path) -> Report:
    report = Report()
    state = read_state(workspace)
    required = ["paper_draft.md", "support_materials_manifest.md"]
    if quality_contract_enabled(state):
        required.append("results/result_registry.json")
    require_files(report, workspace, tuple(required))
    if quality_contract_enabled(state):
        quality_ids = validate_quality_contract(report, workspace)
        validate_result_registry(report, workspace, state, quality_ids)
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
    required = ["paper.md"]
    if quality_contract_enabled(state):
        required.append("results/result_registry.json")
    require_files(report, workspace, tuple(required))
    if quality_contract_enabled(state):
        quality_ids = validate_quality_contract(report, workspace)
        validate_result_registry(report, workspace, state, quality_ids)
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
