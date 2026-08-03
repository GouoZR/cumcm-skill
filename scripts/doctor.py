#!/usr/bin/env python3
"""Preflight checks for the cumcm-skill package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
COMPETITIONS = ("cumcm",)
COMPETITION_FILES = (
    "README.md",
    "winning_patterns.md",
    "phrase_bank.md",
    "anti_patterns.md",
    "abstract_template.md",
    "paper_skeleton.md",
    "rubric_overlay.json",
    "topic_specs.json",
    "empirical.json",
    "empirical_notes.md",
    "current_rules.md",
)
MODELING_MODULES = ("numpy", "scipy", "pandas", "matplotlib", "sklearn")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    fix: str | None = None


def _check(name: str, ok: bool, detail: str, fix: str | None = None) -> Check:
    return Check(name=name, status="pass" if ok else "fail", detail=detail, fix=fix)


def _optional(name: str, ok: bool, detail: str, fix: str | None = None) -> Check:
    return Check(name=name, status="pass" if ok else "warn", detail=detail, fix=fix)


def _load_json(path: Path) -> tuple[bool, object | str]:
    try:
        return True, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)


def _frontmatter_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"\A---\s*\n.*?^name:\s*[\"']?([^\n\"']+)", text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else None


def _anti_pattern_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^###\s+[A-Z]\d+\.\s", text, re.MULTILINE))


def run_checks(
    competition: str,
    workspace: Path | None = None,
    require_modeling: bool = False,
) -> list[Check]:
    checks: list[Check] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(_check(
        "python",
        py_ok,
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Install Python 3.10 or newer." if not py_ok else None,
    ))

    required_paths = (
        "SKILL.md",
        "README.md",
        "AGENTS.md",
        "config/dim_weights.json",
        "templates/shared/workflow_state.json",
        "templates/shared/capabilities.json",
        "templates/shared/artifact_manifest.json",
        "templates/shared/handoff.md",
        "templates/shared/subagent_report.md",
        "templates/shared/final_review.md",
        "templates/shared/decision_log.json",
        "scripts/init_workspace.py",
        "scripts/workflow.py",
        "scripts/validate_handoff.py",
        "scripts/validate_literature.py",
        "scripts/assemble_paper.py",
        "scripts/score_artifact.py",
        "scripts/extract_diff.py",
        "scripts/render_ai_usage.py",
        "templates/shared/ai_usage_ledger.json",
        "references/runtime/codex.md",
        "references/runtime/codex_subagents.md",
        "references/runtime/claude_code.md",
        "references/handoff_protocol.md",
        *tuple(f"references/workflow/stage_{stage:02d}_{name}.md" for stage, name in (
            (0, "claude_intake"),
            (1, "codex_modeling"),
            (2, "claude_implementation"),
            (3, "codex_audit"),
            (4, "claude_writing"),
            (5, "codex_final_review"),
            (6, "claude_delivery"),
        )),
    )
    missing = [item for item in required_paths if not (SKILL_ROOT / item).is_file()]
    checks.append(_check(
        "package-structure",
        not missing,
        "all core entrypoints present" if not missing else f"missing: {', '.join(missing)}",
    ))

    skill_name = _frontmatter_name(SKILL_ROOT / "SKILL.md")
    checks.append(_check(
        "skill-metadata",
        skill_name == "cumcm-skill",
        f"root={skill_name!r}",
    ))

    json_paths = [
        SKILL_ROOT / "config" / "dim_weights.json",
        SKILL_ROOT / "templates" / "shared" / "workflow_state.json",
        SKILL_ROOT / "templates" / "shared" / "capabilities.json",
        SKILL_ROOT / "templates" / "shared" / "artifact_manifest.json",
        SKILL_ROOT / "templates" / "shared" / "literature_library.json",
        SKILL_ROOT / "templates" / "shared" / "literature_claim_map.json",
        SKILL_ROOT / "templates" / "shared" / "final_patch_plan.json",
        SKILL_ROOT / "templates" / "shared" / "decision_log.json",
        SKILL_ROOT / "templates" / "shared" / "ai_usage_ledger.json",
    ]
    for comp in COMPETITIONS:
        json_paths.extend((
            SKILL_ROOT / "competitions" / comp / "rubric_overlay.json",
            SKILL_ROOT / "competitions" / comp / "topic_specs.json",
            SKILL_ROOT / "competitions" / comp / "empirical.json",
        ))
    invalid_json = []
    parsed: dict[Path, object] = {}
    for path in json_paths:
        ok, value = _load_json(path)
        if ok:
            parsed[path] = value
        else:
            invalid_json.append(f"{path.relative_to(SKILL_ROOT)}: {value}")
    checks.append(_check(
        "json-config",
        not invalid_json,
        f"{len(json_paths)} files parsed" if not invalid_json else "; ".join(invalid_json),
    ))

    decision_path = SKILL_ROOT / "templates" / "shared" / "decision_log.json"
    decision = parsed.get(decision_path, {})
    decision_schema_ok = (
        isinstance(decision, dict)
        and decision.get("_schema_version") == "3.1"
        and isinstance(decision.get("stages"), dict)
        and isinstance(decision.get("scores"), dict)
        and isinstance(decision.get("iterations"), dict)
        and isinstance(decision.get("compliance"), dict)
        and isinstance(decision.get("compliance", {}).get("ruleset"), dict)
        and "ai_usage" in decision.get("compliance", {})
    )
    checks.append(_check(
        "decision-log-schema",
        decision_schema_ok,
        "decision_log schema 3.1 with compliance state"
        if decision_schema_ok else "decision_log template is not a complete v3.1 state",
        "Restore the v3.1 decision-log template before using the workflow."
        if not decision_schema_ok else None,
    ))

    workflow_template_path = SKILL_ROOT / "templates" / "shared" / "workflow_state.json"
    workflow_template = parsed.get(workflow_template_path, {})
    workflow_schema_ok = (
        isinstance(workflow_template, dict)
        and workflow_template.get("_schema_version") == "4.0"
        and workflow_template.get("current_stage") == 0
        and workflow_template.get("current_owner") == "claude"
        and workflow_template.get("revision") == 0
        and isinstance(workflow_template.get("completed_stages"), list)
        and isinstance(workflow_template.get("blocking_issues"), list)
    )
    checks.append(_check(
        "workflow-schema",
        workflow_schema_ok,
        "workflow schema 4.0 with owner/revision guards"
        if workflow_schema_ok else "workflow_state template is not a complete v4.0 state",
        "Restore templates/shared/workflow_state.json before using v2."
        if not workflow_schema_ok else None,
    ))

    patch_plan_path = SKILL_ROOT / "templates" / "shared" / "final_patch_plan.json"
    patch_plan = parsed.get(patch_plan_path, {})
    patch_contract = (
        patch_plan.get("_patch_item_contract", {})
        if isinstance(patch_plan, dict)
        else {}
    )
    required_patch_fields = {
        "id",
        "target",
        "severity",
        "problem",
        "evidence",
        "action",
        "acceptance_check",
        "status",
    }
    patch_plan_schema_ok = (
        isinstance(patch_plan, dict)
        and patch_plan.get("_schema_version") == "1.0"
        and (patch_plan.get("verdict"), patch_plan.get("target_stage"))
        in {("passed", 6), ("needs_revision", 4)}
        and isinstance(patch_plan.get("patches"), list)
        and isinstance(patch_contract, dict)
        and required_patch_fields.issubset(
            set(patch_contract.get("required_fields", []))
        )
        and {"file", "anchor"}.issubset(
            set(patch_contract.get("target_required_fields", []))
        )
        and set(patch_contract.get("severity_values", []))
        == {"blocker", "high", "medium", "low"}
        and {"pending", "applied", "verified"}.issubset(
            set(patch_contract.get("status_values", []))
        )
    )
    checks.append(_check(
        "final-patch-plan-schema",
        patch_plan_schema_ok,
        "final patch plan schema 1.0 with executable item contract"
        if patch_plan_schema_ok else "final_patch_plan template lacks the required patch item contract",
        "Restore templates/shared/final_patch_plan.json with the documented item fields."
        if not patch_plan_schema_ok else None,
    ))

    comp_dir = SKILL_ROOT / "competitions" / competition
    missing_comp = [name for name in COMPETITION_FILES if not (comp_dir / name).is_file()]
    checks.append(_check(
        "competition-pack",
        not missing_comp,
        f"{competition}: {len(COMPETITION_FILES)} required files"
        if not missing_comp else f"{competition} missing: {', '.join(missing_comp)}",
    ))

    # 可选资产：distilled_* 为按需加载的模板，缺失仅告警（SKILL.md 加载协议已登记）
    optional_assets = ("distilled_phrases.md", "distilled_structures.md",
                       "distilled_naming.md", "distilled_formats.md")
    missing_optional = [name for name in optional_assets if not (comp_dir / name).is_file()]
    checks.append(_optional(
        "optional-assets",
        not missing_optional,
        f"{competition}: optional distilled templates present"
        if not missing_optional else f"{competition} missing optional: {', '.join(missing_optional)}",
        "Restore the distilled template files or remove their registration from SKILL.md."
        if missing_optional else None,
    ))

    # 可选资产：archive/ 真题库（真题建模档案 + 优秀论文标答），缺失仅告警
    archive_dir = comp_dir / "archive"
    missing_archive = []
    if not archive_dir.is_dir():
        missing_archive.append("archive/")
    elif not (archive_dir / "README.md").is_file():
        missing_archive.append("archive/README.md")
    checks.append(_optional(
        "archive-assets",
        not missing_archive,
        f"{competition}: archive/ 真题库 present"
        if not missing_archive else f"{competition} missing: {', '.join(missing_archive)}",
        "Create competitions/cumcm/archive/ with README.md (真题建模档案 + 优秀论文标答)."
        if missing_archive else None,
    ))

    anti_path = comp_dir / "anti_patterns.md"
    if anti_path.is_file():
        anti_count = _anti_pattern_count(anti_path)
        checks.append(_check(
            "anti-pattern-index",
            anti_count > 0,
            f"{competition}: {anti_count} indexed checks",
        ))
        declared = (
            decision.get("stages", {}).get("9", {})
            .get("anti_patterns_check", {}).get("total")
            if isinstance(decision, dict) else None
        )
        checks.append(_check(
            "anti-pattern-state-init",
            declared is None,
            f"template defers total; {competition} source currently has {anti_count}",
            "Keep the shared template total null; Stage 9 initializes it from the active competition pack."
            if declared is not None else None,
        ))

    if workspace:
        workflow_path = workspace / "state" / "workflow.json"
        decision_path = workspace / "state" / "decision_log.json"
        if workflow_path.is_file():
            ok, value = _load_json(workflow_path)
            valid = (
                ok and isinstance(value, dict)
                and value.get("_schema_version") == "4.0"
                and value.get("competition") == competition
                and isinstance(value.get("current_stage"), int)
                and not isinstance(value.get("current_stage"), bool)
                and 0 <= value["current_stage"] <= 6
                and value.get("current_owner") in {"claude", "codex", "user"}
                and isinstance(value.get("revision"), int)
                and not isinstance(value.get("revision"), bool)
                and value["revision"] >= 0
                and isinstance(value.get("completed_stages"), list)
                and isinstance(value.get("blocking_issues"), list)
            )
            checks.append(_check(
                "workspace-state",
                valid,
                str(workflow_path) if valid else f"invalid v4 state: {value}",
            ))
        elif decision_path.is_file():
            ok, value = _load_json(decision_path)
            compliance = value.get("compliance") if isinstance(value, dict) else None
            valid = (
                ok and isinstance(value, dict)
                and value.get("_schema_version") == "3.1"
                and value.get("competition") == competition
                and isinstance(value.get("current_stage"), int)
                and not isinstance(value.get("current_stage"), bool)
                and 0 <= value["current_stage"] <= 9
                and isinstance(value.get("stages"), dict)
                and isinstance(value.get("scores"), dict)
                and isinstance(value.get("iterations"), dict)
                and isinstance(compliance, dict)
                and isinstance(compliance.get("ruleset"), dict)
                and "ai_usage" in compliance
            )
            checks.append(_check(
                "workspace-state",
                valid,
                f"legacy v1 state: {decision_path}" if valid else f"invalid state: {value}",
            ))
        else:
            checks.append(_optional(
                "workspace-state",
                False,
                f"not initialized: {workflow_path}",
                "Run scripts/init_workspace.py for a v2 workspace.",
            ))

    if require_modeling:
        missing_modules = [name for name in MODELING_MODULES if importlib.util.find_spec(name) is None]
        checks.append(_check(
            "modeling-stack",
            not missing_modules,
            "core modeling modules found" if not missing_modules else f"missing: {', '.join(missing_modules)}",
            "Install templates/shared/requirements.txt." if missing_modules else None,
        ))

    return checks


def _print_human(checks: list[Check]) -> None:
    symbols = {"pass": "✓", "warn": "!", "fail": "✗"}
    for item in checks:
        print(f"{symbols[item.status]} {item.name}: {item.detail}")
        if item.fix and item.status != "pass":
            print(f"  ↳ {item.fix}")
    counts = {status: sum(item.status == status for item in checks) for status in symbols}
    print(
        f"\nSummary: {counts['pass']} passed, "
        f"{counts['warn']} optional warnings, {counts['fail']} failed"
    )


def main() -> int:
    # Windows 控制台默认 GBK；强制 UTF-8 输出，避免子进程按 utf-8 捕获中文时崩溃。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass

    parser = argparse.ArgumentParser(description="Check cumcm-skill readiness.")
    parser.add_argument("--competition", choices=COMPETITIONS, default="cumcm")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--require-modeling", action="store_true")
    args = parser.parse_args()

    checks = run_checks(
        competition=args.competition,
        workspace=args.workspace.resolve() if args.workspace else None,
        require_modeling=args.require_modeling,
    )
    if args.as_json:
        print(json.dumps([asdict(item) for item in checks], ensure_ascii=False, indent=2))
    else:
        _print_human(checks)
    return 1 if any(item.status == "fail" for item in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
