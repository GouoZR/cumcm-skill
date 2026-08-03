#!/usr/bin/env python3
"""Tests for the programmatic Stage 2/4/6 preflight and its workflow wiring."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cumcm_preflight_test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


init_workspace = load_script("init_workspace")
validate_stage = load_script("validate_stage")
validate_handoff = load_script("validate_handoff")
workflow = load_script("workflow")

# 1x1 灰度 PNG，用于让图表路径检查有真实文件可解析。
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108000000003a7e9b55"
    "0000000a4944415408d76360000000020001e221bc330000000049454e44ae426082"
)


def sha256_of(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


PAPER_BODY = """# 某问题的建模与求解

## 摘要

本文用线性规划求解配置问题，最优目标值 12.5，并做了敏感性验证[1]。

## 问题分析

题目要求在容量约束下最大化收益，见文献[2]的处理方式。

## 模型建立

目标函数与约束按规格给出。

## 结果与分析

最优目标值 12.5。

![问题一最优解](figures/q1_result.png)

## 参考文献

[1] 张三. 线性规划在资源配置中的应用. 运筹学学报, 2020.
[2] 李四. 约束优化的敏感性分析. 系统工程理论与实践, 2021.
"""


def register(workspace: Path, entries: list[dict[str, object]]) -> None:
    path = workspace / "state" / "artifact_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["artifacts"] = entries
    write_json(path, manifest)


def artifact(workspace: Path, relative: str, stage: int, owner: str, status: str) -> dict:
    return {
        "path": relative,
        "stage": stage,
        "owner": owner,
        "status": status,
        "sha256": sha256_of(workspace / relative),
        "inputs": [],
    }


def quality_contract_fixture() -> dict[str, object]:
    return {
        "_schema_version": "1.0",
        "subproblems": [{
            "id": "q1",
            "problem_type": "optimization",
            "question_target": "求可行方案的最优目标值",
            "analysis_unit": "候选方案",
            "output_definition": "最优可行方案及目标值",
            "metric_definition": "目标函数值",
            "aggregation_scope": "对单个方案计算，不跨方案重复计数",
            "constraints": ["满足题面资源约束"],
            "invariants": [{
                "id": "INV-Q1-01",
                "statement": "输出方案必须满足全部约束",
                "check": "读取结果并计算最大约束违反量",
                "expected": "最大违反量等于 0",
            }],
            "baseline_or_oracle": "小规模枚举基线",
            "fidelity_and_discretization": ["本例为离散小规模问题，无额外离散化"],
            "claim_boundaries": ["结论仅适用于当前输入数据和约束"],
        }],
    }


def result_registry_fixture(run_id: str) -> dict[str, object]:
    return {
        "_schema_version": "1.0",
        "run_id": run_id,
        "result_version": "test-v1",
        "metrics": [{
            "id": "Q1.primary_objective",
            "subproblem": "q1",
            "role": "primary",
            "name": "最优目标值",
            "value": 12.5,
            "unit": "无量纲",
            "direction": "maximize",
            "scope": "当前测试输入和资源约束",
            "source": "results/q1_result.csv",
            "source_locator": "objective 列第 1 行",
            "method": "测试求解器",
            "seed": 20260803,
            "evidence": ["figures/q1_result.png"],
        }],
    }


def build_stage2_workspace(workspace: Path) -> dict[str, object]:
    """A minimal workspace that legitimately passes the Stage 2 preflight."""
    (workspace / "input").mkdir(parents=True, exist_ok=True)
    (workspace / "input" / "problem.md").write_text("题面\n", encoding="utf-8")
    result = init_workspace.initialize(workspace)

    (workspace / "artifacts" / "problem_analysis.md").write_text("# 分析\n内容\n", encoding="utf-8")
    (workspace / "artifacts" / "model_spec.md").write_text("# 规格\n目标函数\n", encoding="utf-8")
    (workspace / "artifacts" / "implementation_contract.md").write_text(
        "# 契约\n复现命令\n", encoding="utf-8"
    )
    (workspace / "artifacts" / "model_deviations.md").write_text(
        "# 模型偏离\n无偏离。\n", encoding="utf-8"
    )
    (workspace / "code" / "q1_solve.py").write_text("print('solved')\n", encoding="utf-8")
    (workspace / "results" / "q1_result.csv").write_text("objective\n12.5\n", encoding="utf-8")
    (workspace / "figures").mkdir(parents=True, exist_ok=True)
    (workspace / "figures" / "q1_result.png").write_bytes(PNG_BYTES)
    write_json(workspace / "artifacts" / "quality_contract.json", quality_contract_fixture())
    write_json(
        workspace / "results" / "result_registry.json",
        result_registry_fixture(str(result["run_id"])),
    )

    manifest_path = workspace / "artifacts" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        spec_checksum=sha256_of(workspace / "artifacts" / "model_spec.md"),
        quality_contract_checksum=sha256_of(
            workspace / "artifacts" / "quality_contract.json"
        ),
        environment="python 3.12; numpy 2.1",
        subproblems=[{
            "id": "q1",
            "command": "python code/q1_solve.py",
            "seed": 20260803,
            "code": ["code/q1_solve.py"],
            "results": ["results/q1_result.csv"],
            "figures": ["figures/q1_result.png"],
        }],
    )
    write_json(manifest_path, manifest)

    register(workspace, [
        artifact(workspace, "artifacts/model_spec.md", 1, "codex", "verified"),
        artifact(workspace, "code/q1_solve.py", 2, "claude", "verified"),
        artifact(workspace, "results/q1_result.csv", 2, "claude", "verified"),
        artifact(workspace, "figures/q1_result.png", 2, "claude", "verified"),
        artifact(workspace, "artifacts/quality_contract.json", 1, "codex", "verified"),
        artifact(workspace, "results/result_registry.json", 2, "claude", "verified"),
    ])
    return result


def build_stage4_artifacts(workspace: Path) -> None:
    (workspace / "paper_draft.md").write_text(PAPER_BODY, encoding="utf-8")
    (workspace / "support_materials_manifest.md").write_text(
        "# 支撑材料\n\n- `code/q1_solve.py`：问题一求解脚本\n", encoding="utf-8"
    )
    (workspace / "paper_workspace").mkdir(parents=True, exist_ok=True)
    (workspace / "paper_workspace" / "01_abstract.md").write_text(
        "## 摘要\n最优目标值 12.5。\n", encoding="utf-8"
    )
    (workspace / "paper_workspace" / "02_model.md").write_text(
        "## 模型建立\n目标函数与约束。\n", encoding="utf-8"
    )


def build_stage6_artifacts(workspace: Path, patches: list[dict[str, object]] | None = None) -> None:
    (workspace / "paper.md").write_text(PAPER_BODY, encoding="utf-8")
    write_json(workspace / "reviews" / "final_patch_plan.json", {
        "_schema_version": "1.0",
        "verdict": "passed",
        "target_stage": 6,
        "patches": patches if patches is not None else [{
            "id": "P1",
            "target": {"file": "paper.md", "anchor": "## 摘要"},
            "severity": "medium",
            "problem": "摘要缺少验证方式",
            "evidence": "final_review.md 第 2 节",
            "action": "补充敏感性验证一句",
            "acceptance_check": "摘要含验证方式",
            "status": "verified",
        }],
    })
    entries = [
        artifact(workspace, "results/q1_result.csv", 2, "claude", "verified"),
        artifact(workspace, "figures/q1_result.png", 2, "claude", "verified"),
        artifact(workspace, "paper.md", 6, "claude", "final"),
    ]
    register(workspace, entries)


class Stage2PreflightTests(unittest.TestCase):
    def test_minimal_valid_workspace_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertTrue(report.ok, report.errors)

    def test_fresh_workspace_run_manifest_is_rejected_until_filled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "input").mkdir()
            (workspace / "input" / "problem.md").write_text("题面\n", encoding="utf-8")
            init_workspace.initialize(workspace)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("spec_checksum" in item for item in report.errors))
            self.assertTrue(any("subproblems" in item for item in report.errors))

    def test_new_workspace_creates_quality_gate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "input").mkdir()
            (workspace / "input" / "problem.md").write_text("题面\n", encoding="utf-8")
            result = init_workspace.initialize(workspace)
            state = workflow.load_state(workspace)
            registry = json.loads(
                (workspace / "results" / "result_registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["quality_contract_version"], "1.0")
            self.assertTrue((workspace / "artifacts" / "quality_contract.json").is_file())
            self.assertEqual(registry["run_id"], result["run_id"])

    def test_missing_quality_contract_fails_for_new_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            (workspace / "artifacts" / "quality_contract.json").unlink()
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("quality_contract.json" in item for item in report.errors))

    def test_empty_quality_contract_subproblems_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "artifacts" / "quality_contract.json"
            write_json(path, {"_schema_version": "1.0", "subproblems": []})
            manifest_path = workspace / "artifacts" / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["quality_contract_checksum"] = sha256_of(path)
            write_json(manifest_path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("subproblems 必须是非空数组" in item for item in report.errors))

    def test_quality_contract_and_run_manifest_ids_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "artifacts" / "quality_contract.json"
            contract = json.loads(path.read_text(encoding="utf-8"))
            contract["subproblems"][0]["id"] = "q2"
            write_json(path, contract)
            manifest_path = workspace / "artifacts" / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["quality_contract_checksum"] = sha256_of(path)
            write_json(manifest_path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("id 必须完全一致" in item for item in report.errors))

    def test_result_registry_requires_primary_metric_per_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "results" / "result_registry.json"
            registry = json.loads(path.read_text(encoding="utf-8"))
            registry["metrics"][0]["role"] = "validation"
            write_json(path, registry)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("至少需要一个 primary" in item for item in report.errors))

    def test_result_registry_source_and_evidence_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "results" / "result_registry.json"
            registry = json.loads(path.read_text(encoding="utf-8"))
            registry["metrics"][0]["source"] = "results/missing.csv"
            registry["metrics"][0]["evidence"] = ["figures/missing.png"]
            write_json(path, registry)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("missing.csv" in item for item in report.errors))
            self.assertTrue(any("missing.png" in item for item in report.errors))

    def test_stale_quality_contract_checksum_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "artifacts" / "quality_contract.json"
            contract = json.loads(path.read_text(encoding="utf-8"))
            contract["subproblems"][0]["claim_boundaries"].append("新增边界")
            write_json(path, contract)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("quality_contract_checksum" in item for item in report.errors))

    def test_legacy_workspace_without_feature_flag_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            state_path = workspace / "state" / "workflow.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.pop("quality_contract_version", None)
            write_json(state_path, state)
            (workspace / "artifacts" / "quality_contract.json").unlink()
            (workspace / "results" / "result_registry.json").unlink()
            manifest_path = workspace / "artifacts" / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("quality_contract_checksum", None)
            manifest.pop("result_registry", None)
            write_json(manifest_path, manifest)
            artifact_path = workspace / "state" / "artifact_manifest.json"
            artifact_manifest = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_manifest["artifacts"] = [
                entry for entry in artifact_manifest["artifacts"]
                if entry["path"] not in {
                    "artifacts/quality_contract.json",
                    "results/result_registry.json",
                }
            ]
            write_json(artifact_path, artifact_manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertTrue(report.ok, report.errors)

    def test_missing_run_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            (workspace / "artifacts" / "run_manifest.json").unlink()
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("run_manifest.json" in item for item in report.errors))

    def test_declared_result_that_does_not_exist_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            (workspace / "results" / "q1_result.csv").unlink()
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("不存在" in item for item in report.errors))

    def test_subproblem_without_figure_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "artifacts" / "run_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["subproblems"][0]["figures"] = []
            write_json(path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("figures 必须是非空数组" in item for item in report.errors))

    def test_stale_spec_checksum_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            (workspace / "artifacts" / "model_spec.md").write_text(
                "# 规格\n目标函数已改\n", encoding="utf-8"
            )
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("spec_checksum" in item for item in report.errors))


    def test_run_manifest_outputs_must_be_registered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            register(workspace, [])
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("未登记到 artifact manifest" in item for item in report.errors))

    def test_registered_run_output_cannot_be_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "state" / "artifact_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["artifacts"][1]["status"] = "stale"
            write_json(path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("不得进入 Stage 3" in item for item in report.errors))


class ArtifactManifestTests(unittest.TestCase):
    def test_wrong_checksum_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "state" / "artifact_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["artifacts"][1]["sha256"] = "sha256:" + "0" * 64
            write_json(path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("sha256 与文件当前内容不一致" in item for item in report.errors))

    def test_duplicate_path_and_illegal_status_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            entry = artifact(workspace, "results/q1_result.csv", 2, "claude", "verified")
            bad_status = dict(entry, status="published")
            register(workspace, [entry, dict(entry), bad_status])
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("path 重复登记" in item for item in report.errors))
            self.assertTrue(any("status 必须属于" in item for item in report.errors))

    def test_path_outside_workspace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            entry = artifact(workspace, "results/q1_result.csv", 2, "claude", "verified")
            register(workspace, [dict(entry, path="../outside.csv")])
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("逃出工作区" in item for item in report.errors))


    def test_owner_must_match_artifact_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "state" / "artifact_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["artifacts"][1]["owner"] = "codex"
            write_json(path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("Stage 2 的 owner 必须是 claude" in item for item in report.errors))

    def test_artifact_input_must_stay_inside_workspace_and_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            path = workspace / "state" / "artifact_manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["artifacts"][1]["inputs"] = ["../outside.csv", "input/missing.csv"]
            write_json(path, manifest)
            report = validate_stage.validate_stage(workspace, 2)
            self.assertFalse(report.ok)
            self.assertTrue(any("inputs[0] 路径逃出工作区" in item for item in report.errors))
            self.assertTrue(any("inputs[1] 声明的输入不存在" in item for item in report.errors))


class Stage4PreflightTests(unittest.TestCase):
    def prepare(self, workspace: Path) -> None:
        build_stage2_workspace(workspace)
        build_stage4_artifacts(workspace)

    def test_valid_draft_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            report = validate_stage.validate_stage(workspace, 4)
            self.assertTrue(report.ok, report.errors)

    def test_todo_marker_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            draft = workspace / "paper_draft.md"
            draft.write_text(
                draft.read_text(encoding="utf-8") + "\nTODO: 补敏感性分析\n", encoding="utf-8"
            )
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("残留标记 TODO" in item for item in report.errors))

    def test_template_placeholder_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            draft = workspace / "paper_draft.md"
            draft.write_text(
                draft.read_text(encoding="utf-8") + "\n作者：<待填>\n", encoding="utf-8"
            )
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("残留模板占位符" in item for item in report.errors))

    def test_broken_image_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            (workspace / "figures" / "q1_result.png").unlink()
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("图片路径不存在" in item for item in report.errors))

    def test_windows_absolute_image_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            draft = workspace / "paper_draft.md"
            draft.write_text(
                draft.read_text(encoding="utf-8") + "\n![绝对路径](C:\\temp\\figure.png)\n",
                encoding="utf-8",
            )
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("图片必须使用相对路径" in item for item in report.errors))

    def test_missing_reference_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            draft = workspace / "paper_draft.md"
            draft.write_text(
                draft.read_text(encoding="utf-8").replace("敏感性验证[1]", "敏感性验证[7]"),
                encoding="utf-8",
            )
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("引用 [7]" in item for item in report.errors))

    def test_empty_section_and_credential_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            draft = workspace / "paper_draft.md"
            draft.write_text(
                draft.read_text(encoding="utf-8")
                + "\n## 模型评价\n\n## 附录\nAPI_KEY = 'sk-abcdefghijklmnopqrstuvwx012345'\n",
                encoding="utf-8",
            )
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("章节为空: 模型评价" in item for item in report.errors))
            self.assertTrue(any("疑似凭据" in item for item in report.errors))

    def test_figure_marked_needs_revision_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            register(workspace, [
                artifact(workspace, "figures/q1_result.png", 2, "claude", "needs_revision"),
            ])
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("needs_revision 的图" in item for item in report.errors))

    def test_missing_paper_workspace_sections_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            for path in (workspace / "paper_workspace").glob("*.md"):
                path.unlink()
            report = validate_stage.validate_stage(workspace, 4)
            self.assertFalse(report.ok)
            self.assertTrue(any("paper_workspace/" in item for item in report.errors))


class Stage6PreflightTests(unittest.TestCase):
    def prepare(self, workspace: Path, patches: list[dict[str, object]] | None = None) -> None:
        build_stage2_workspace(workspace)
        build_stage4_artifacts(workspace)
        build_stage6_artifacts(workspace, patches)

    def test_valid_delivery_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            report = validate_stage.validate_stage(workspace, 6)
            self.assertTrue(report.ok, report.errors)

    def test_empty_paper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            (workspace / "paper.md").write_text("   \n", encoding="utf-8")
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("paper.md" in item for item in report.errors))

    def test_patch_required_text_fields_cannot_be_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace, [{
                "id": "P1",
                "target": {"file": "paper.md", "anchor": "## 摘要"},
                "severity": "medium",
                "problem": "",
                "evidence": "final_review.md 第 2 节",
                "action": "补一句验证",
                "acceptance_check": "摘要含验证方式",
                "status": "verified",
            }])
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("problem 必须是非空字符串" in item for item in report.errors))

    def test_pending_patch_blocks_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace, [{
                "id": "P1",
                "target": {"file": "paper.md", "anchor": "## 摘要"},
                "severity": "medium",
                "problem": "摘要缺少验证方式",
                "evidence": "final_review.md 第 2 节",
                "action": "补一句验证",
                "acceptance_check": "摘要含验证方式",
                "status": "pending",
            }])
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("仍是 pending" in item for item in report.errors))

    def test_blocker_cannot_be_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace, [{
                "id": "P1",
                "target": {"file": "paper.md", "anchor": "## 结果与分析"},
                "severity": "blocker",
                "problem": "结果与 results/ 不一致",
                "evidence": "final_review.md 第 3 节",
                "action": "改回已验证数值",
                "acceptance_check": "数值一致",
                "status": "accepted",
                "resolution_note": "时间不够，先接受",
            }])
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("不得用 accepted 跳过" in item for item in report.errors))

    def test_accepted_requires_resolution_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace, [{
                "id": "P1",
                "target": {"file": "paper.md", "anchor": "## 摘要"},
                "severity": "low",
                "problem": "措辞可优化",
                "evidence": "final_review.md 第 4 节",
                "action": "可选润色",
                "acceptance_check": "措辞一致",
                "status": "accepted",
            }])
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("resolution_note" in item for item in report.errors))

    def test_paper_not_registered_as_final_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self.prepare(workspace)
            register(workspace, [
                artifact(workspace, "figures/q1_result.png", 2, "claude", "verified"),
                artifact(workspace, "paper.md", 6, "claude", "draft"),
            ])
            report = validate_stage.validate_stage(workspace, 6)
            self.assertFalse(report.ok)
            self.assertTrue(any("应为 final" in item for item in report.errors))


HANDOFF_TEMPLATE = """# Handoff {name}

- From: {from_actor}
- To: {to_actor}
- Completed Stage: {completed_stage}
- Next Stage: {next_stage}
- Workflow Revision: {revision}
- Acceptance: {acceptance}

## 已完成内容

- 完成本阶段全部产物

## 新增或修改文件

- `artifacts/run_manifest.json`：登记运行清单

## 已执行验证

- `validate_stage.py --stage {completed_stage}`：通过

## 已冻结事实与决策

- 无

## SubAgent 并行产出轨迹（Claude Stage 2/4）

- Partitions: `q1`
- Main-agent verification: `复跑 q1 决定性结果并核对图表数字`
- Rejected or reworked output: `无`
- Fallback mode: `serial-main-agent`

## 未解决问题

- 无

## 下一位 Agent 的明确任务

1. 审计模型—代码—结果一致性

## 禁止修改的文件

- 无

## 验收说明

- 预检通过，可进入下一阶段
"""

UNFILLED_HANDOFF = (ROOT / "templates" / "shared" / "handoff.md").read_text(encoding="utf-8")


def write_handoff(workspace: Path, name: str, **kwargs) -> Path:
    path = workspace / "state" / "handoffs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HANDOFF_TEMPLATE.format(name=name.split(".")[0], **kwargs), encoding="utf-8")
    return path


class HandoffSubstanceTests(unittest.TestCase):
    def test_unfilled_template_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "handoff.md"
            path.write_text(UNFILLED_HANDOFF, encoding="utf-8")
            ok, errors, _ = validate_handoff.validate_handoff(path)
            self.assertFalse(ok)
            self.assertTrue(any("章节未填写" in item for item in errors))

    def test_filled_handoff_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            path = write_handoff(
                workspace,
                "H005.md",
                from_actor="claude",
                to_actor="codex",
                completed_stage=2,
                next_stage=3,
                revision=5,
                acceptance="passed",
            )
            ok, errors, _ = validate_handoff.validate_handoff(path, "claude", "codex", 3)
            self.assertTrue(ok, errors)

    def test_stage2_requires_subagent_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            path = write_handoff(
                workspace,
                "H005.md",
                from_actor="claude",
                to_actor="codex",
                completed_stage=2,
                next_stage=3,
                revision=5,
                acceptance="passed",
            )
            text = path.read_text(encoding="utf-8")
            start = text.index("## SubAgent 并行产出轨迹")
            stop = text.index("## 未解决问题")
            path.write_text(text[:start] + text[stop:], encoding="utf-8")
            ok, errors, _ = validate_handoff.validate_handoff(path, "claude", "codex", 3)
            self.assertFalse(ok)
            self.assertTrue(any("SubAgent 并行产出轨迹" in item for item in errors))

    def test_fallback_none_requires_partitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            path = write_handoff(
                workspace,
                "H005.md",
                from_actor="claude",
                to_actor="codex",
                completed_stage=2,
                next_stage=3,
                revision=5,
                acceptance="passed",
            )
            text = path.read_text(encoding="utf-8")
            text = text.replace("- Partitions: `q1`", "- Partitions: `无`")
            text = text.replace("`serial-main-agent`", "`none`")
            path.write_text(text, encoding="utf-8")
            ok, errors, _ = validate_handoff.validate_handoff(path, "claude", "codex", 3)
            self.assertFalse(ok)
            self.assertTrue(any("必须列出实际分区" in item for item in errors))


def force_state(workspace: Path, **updates) -> None:
    path = workspace / "state" / "workflow.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    workflow.atomic_write(path, state)


class WorkflowPreflightWiringTests(unittest.TestCase):
    def test_stage2_handoff_is_blocked_until_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            (workspace / "artifacts" / "run_manifest.json").unlink()
            force_state(
                workspace,
                current_stage=2,
                current_owner="claude",
                status="in_progress",
                revision=5,
                completed_stages=[0, 1],
            )
            path = write_handoff(
                workspace,
                "H005.md",
                from_actor="claude",
                to_actor="codex",
                completed_stage=2,
                next_stage=3,
                revision=5,
                acceptance="passed",
            )
            with self.assertRaises(workflow.WorkflowError) as caught:
                workflow.handoff(workspace, "claude", "codex", 3, path, 5, "passed")
            self.assertIn("Stage 2 预检失败", str(caught.exception))
            # 预检失败不得改状态
            state = workflow.load_state(workspace)
            self.assertEqual(state["revision"], 5)
            self.assertEqual(state["current_stage"], 2)

            manifest = json.loads(
                (ROOT / "templates" / "shared" / "run_manifest.json").read_text(encoding="utf-8")
            )
            manifest.update(
                run_id=state["run_id"],
                input_fingerprint=state["input_fingerprint"],
                spec_checksum=sha256_of(workspace / "artifacts" / "model_spec.md"),
                quality_contract_checksum=sha256_of(
                    workspace / "artifacts" / "quality_contract.json"
                ),
                environment="python 3.12",
                subproblems=[{
                    "id": "q1",
                    "command": "python code/q1_solve.py",
                    "seed": None,
                    "code": ["code/q1_solve.py"],
                    "results": ["results/q1_result.csv"],
                    "figures": ["figures/q1_result.png"],
                }],
            )
            write_json(workspace / "artifacts" / "run_manifest.json", manifest)
            moved = workflow.handoff(workspace, "claude", "codex", 3, path, 5, "passed")
            self.assertEqual(moved["current_stage"], 3)
            self.assertEqual(moved["current_owner"], "codex")

    def test_rollback_3_to_2_skips_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            # 破坏 Stage 2 产物：退回时不应因此被拦住
            (workspace / "artifacts" / "run_manifest.json").unlink()
            force_state(
                workspace,
                current_stage=3,
                current_owner="codex",
                status="in_progress",
                revision=7,
                completed_stages=[0, 1, 2],
            )
            path = write_handoff(
                workspace,
                "H007.md",
                from_actor="codex",
                to_actor="claude",
                completed_stage=3,
                next_stage=2,
                revision=7,
                acceptance="needs_revision",
            )
            moved = workflow.handoff(workspace, "codex", "claude", 2, path, 7, "needs_revision")
            self.assertEqual(moved["current_stage"], 2)
            self.assertEqual(moved["status"], "needs_revision")
            self.assertEqual(moved["completed_stages"], [0, 1])

    def test_rollback_5_to_4_skips_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            build_stage4_artifacts(workspace)
            (workspace / "paper_draft.md").unlink()
            force_state(
                workspace,
                current_stage=5,
                current_owner="codex",
                status="in_progress",
                revision=11,
                completed_stages=[0, 1, 2, 3, 4],
            )
            path = write_handoff(
                workspace,
                "H011.md",
                from_actor="codex",
                to_actor="claude",
                completed_stage=5,
                next_stage=4,
                revision=11,
                acceptance="needs_revision",
            )
            moved = workflow.handoff(workspace, "codex", "claude", 4, path, 11, "needs_revision")
            self.assertEqual(moved["current_stage"], 4)
            self.assertEqual(moved["completed_stages"], [0, 1, 2, 3])

    def test_owner_and_revision_guards_still_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            force_state(
                workspace,
                current_stage=2,
                current_owner="claude",
                status="in_progress",
                revision=5,
                completed_stages=[0, 1],
            )
            path = write_handoff(
                workspace,
                "H005.md",
                from_actor="claude",
                to_actor="codex",
                completed_stage=2,
                next_stage=3,
                revision=5,
                acceptance="passed",
            )
            with self.assertRaises(workflow.WorkflowError) as wrong_owner:
                workflow.handoff(workspace, "codex", "codex", 3, path, 5, "passed")
            self.assertIn("owner", str(wrong_owner.exception))
            with self.assertRaises(workflow.WorkflowError) as stale_revision:
                workflow.handoff(workspace, "claude", "codex", 3, path, 4, "passed")
            self.assertIn("revision", str(stale_revision.exception).lower())
            self.assertEqual(workflow.load_state(workspace)["revision"], 5)


class EndToEndSmokeTests(unittest.TestCase):
    """合法最小工作区能够从 Stage 0 一路走到 complete。"""

    def advance(self, workspace: Path, actor: str, recipient: str, next_stage: int) -> dict:
        state = workflow.load_state(workspace)
        revision = int(state["revision"])
        if state["status"] != "in_progress":
            state = workflow.start(workspace, actor, revision)
            revision = int(state["revision"])
        current_stage = int(state["current_stage"])
        acceptance = "needs_revision" if next_stage < current_stage else "passed"
        path = write_handoff(
            workspace,
            f"H{revision:03d}.md",
            from_actor=actor,
            to_actor=recipient,
            completed_stage=current_stage,
            next_stage=next_stage,
            revision=revision,
            acceptance=acceptance,
        )
        return workflow.handoff(
            workspace, actor, recipient, next_stage, path, revision, acceptance
        )

    def test_minimal_valid_workspace_reaches_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            build_stage2_workspace(workspace)
            self.advance(workspace, "claude", "codex", 1)
            self.advance(workspace, "codex", "claude", 2)
            state = self.advance(workspace, "claude", "codex", 3)
            self.assertEqual(state["current_stage"], 3)

            self.advance(workspace, "codex", "claude", 4)
            build_stage4_artifacts(workspace)
            state = self.advance(workspace, "claude", "codex", 5)
            self.assertEqual(state["current_stage"], 5)

            self.advance(workspace, "codex", "claude", 6)
            build_stage6_artifacts(workspace)
            state = workflow.load_state(workspace)
            state = workflow.start(workspace, "claude", int(state["revision"]))
            final = workflow.complete(workspace, "claude", int(state["revision"]))
            self.assertEqual(final["status"], "complete")
            self.assertEqual(final["completed_stages"], [0, 1, 2, 3, 4, 5, 6])
            self.assertEqual(final["current_owner"], "user")


if __name__ == "__main__":
    unittest.main()
