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
        "AGENTS.md",
        "config/dim_weights.json",
        "templates/shared/decision_log.json",
        "scripts/score_artifact.py",
        "scripts/extract_diff.py",
        "scripts/render_ai_usage.py",
        "templates/shared/ai_usage_ledger.json",
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
        decision_path = workspace / "state" / "decision_log.json"
        if decision_path.is_file():
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
                str(decision_path) if valid else f"invalid state: {value}",
            ))
        else:
            checks.append(_optional(
                "workspace-state",
                False,
                f"not initialized: {decision_path}",
                "Start the skill once; the agent will initialize state automatically.",
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
