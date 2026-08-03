#!/usr/bin/env python3
"""Tests for the v2 shared two-agent workflow."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest

import yaml

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cumcm_v2_test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


init_workspace = load_script("init_workspace")
validate_handoff = load_script("validate_handoff")
workflow = load_script("workflow")
doctor = load_script("doctor")
validate_literature = load_script("validate_literature")
assemble_paper = load_script("assemble_paper")


HANDOFF_BODY = """# Handoff H001

- From: {from_actor}
- To: {to_actor}
- Completed Stage: {completed_stage}
- Next Stage: {next_stage}
- Workflow Revision: {revision}
- Acceptance: {acceptance}

## 已完成内容
- done
## 新增或修改文件
- `artifacts/example.md`
## 已执行验证
- test passed
## 已冻结事实与决策
- frozen
## 未解决问题
- 无
## 下一位 Agent 的明确任务
1. continue
## 禁止修改的文件
- 无
## 验收说明
- ready
"""


class WorkspaceInitializationTests(unittest.TestCase):
    def test_initializes_v4_state_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "input").mkdir()
            (workspace / "input" / "problem.md").write_text("题目", encoding="utf-8")
            result = init_workspace.initialize(workspace)
            state = json.loads((workspace / "state" / "workflow.json").read_text(encoding="utf-8"))
            self.assertEqual(state["_schema_version"], "4.0")
            self.assertEqual(state["current_owner"], "claude")
            self.assertTrue(state["input_fingerprint"].startswith("sha256:"))
            self.assertEqual(result["run_id"], state["run_id"])
            for stage in ("stage_01", "stage_03", "stage_05"):
                self.assertTrue((workspace / "reviews" / "subagents" / stage).is_dir())
            with self.assertRaises(FileExistsError):
                init_workspace.initialize(workspace)

    def test_missing_input_is_recorded_as_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_workspace.initialize(workspace)
            state = workflow.load_state(workspace)
            self.assertTrue(state["blocking_issues"])


class HandoffValidationTests(unittest.TestCase):
    def test_valid_handoff_parses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "handoff.md"
            path.write_text(
                HANDOFF_BODY.format(
                    from_actor="claude",
                    to_actor="codex",
                    completed_stage=0,
                    next_stage=1,
                    revision=1,
                    acceptance="passed",
                ),
                encoding="utf-8",
            )
            ok, errors, fields = validate_handoff.validate_handoff(path, "claude", "codex", 1)
            self.assertTrue(ok, errors)
            self.assertEqual(fields["Workflow Revision"], 1)

    def test_missing_sections_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "handoff.md"
            path.write_text("- From: claude\n", encoding="utf-8")
            ok, errors, _ = validate_handoff.validate_handoff(path)
            self.assertFalse(ok)
            self.assertTrue(any("缺少章节" in error for error in errors))


class WorkflowTransitionTests(unittest.TestCase):
    def make_handoff(
        self,
        workspace: Path,
        name: str,
        from_actor: str,
        to_actor: str,
        current_stage: int,
        next_stage: int,
        revision: int,
        acceptance: str = "passed",
    ) -> Path:
        path = workspace / "state" / "handoffs" / name
        path.write_text(
            HANDOFF_BODY.format(
                from_actor=from_actor,
                to_actor=to_actor,
                completed_stage=current_stage,
                next_stage=next_stage,
                revision=revision,
                acceptance=acceptance,
            ),
            encoding="utf-8",
        )
        return path

    def test_owner_and_revision_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_workspace.initialize(workspace)
            started = workflow.start(workspace, "claude", 0)
            self.assertEqual(started["revision"], 1)
            with self.assertRaises(workflow.WorkflowError):
                workflow.start(workspace, "codex", 1)
            handoff = self.make_handoff(workspace, "H001.md", "claude", "codex", 0, 1, 1)
            moved = workflow.handoff(workspace, "claude", "codex", 1, handoff, 1, "passed")
            self.assertEqual(moved["current_stage"], 1)
            self.assertEqual(moved["current_owner"], "codex")
            with self.assertRaises(workflow.WorkflowError):
                workflow.start(workspace, "codex", 1)

    def test_stage3_can_return_to_stage2(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_workspace.initialize(workspace)
            state_path = workspace / "state" / "workflow.json"
            state = workflow.load_state(workspace)
            state.update(
                current_stage=3,
                current_owner="codex",
                status="in_progress",
                revision=8,
                completed_stages=[0, 1, 2],
            )
            workflow.atomic_write(state_path, state)
            handoff = self.make_handoff(
                workspace, "H009.md", "codex", "claude", 3, 2, 8, "needs_revision"
            )
            moved = workflow.handoff(
                workspace, "codex", "claude", 2, handoff, 8, "needs_revision"
            )
            self.assertEqual(moved["status"], "needs_revision")
            self.assertEqual(moved["completed_stages"], [0, 1])

    def test_complete_requires_paper_md(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_workspace.initialize(workspace)
            state_path = workspace / "state" / "workflow.json"
            state = workflow.load_state(workspace)
            state.update(current_stage=6, current_owner="claude", status="in_progress", revision=12)
            workflow.atomic_write(state_path, state)
            with self.assertRaises(workflow.WorkflowError):
                workflow.complete(workspace, "claude", 12)
            (workspace / "paper.md").write_text("# Paper\n", encoding="utf-8")
            completed = workflow.complete(workspace, "claude", 12)
            self.assertEqual(completed["status"], "complete")
            self.assertEqual(completed["current_owner"], "user")


class V2PackageTests(unittest.TestCase):
    def test_seven_workflow_stage_frontmatters(self) -> None:
        paths = sorted((ROOT / "references" / "workflow").glob("stage_[0-9][0-9]_*.md"))
        self.assertEqual(len(paths), 7)
        stages = []
        owners = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            _, frontmatter, _ = text.split("---", 2)
            metadata = yaml.safe_load(frontmatter)
            stages.append(metadata["stage"])
            owners.append(metadata["owner"])
            self.assertIsInstance(metadata["inputs"], list)
            self.assertIsInstance(metadata["outputs"], list)
        self.assertEqual(stages, list(range(7)))
        self.assertEqual(owners, ["claude", "codex", "claude", "codex", "claude", "codex", "claude"])

    def test_codex_subagent_protocol_is_packaged_and_guarded(self) -> None:
        protocol = (ROOT / "references" / "runtime" / "codex_subagents.md").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "templates" / "shared" / "subagent_report.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "不修改任何共享文件",
            "不调用 `workflow.py start`、`handoff` 或 `complete`",
            "不按票数表决",
            "confirmed blocker",
            "国奖级质量目标",
        ):
            self.assertIn(required, protocol)
        for required in (
            "Reviewed Snapshot",
            "Scope Conclusion",
            "no_issue_found|issues_found|insufficient_evidence",
            "Severity",
            "Evidence",
            "Acceptance Check",
            "未能检查的内容",
        ):
            self.assertIn(required, template)

        final_review = (ROOT / "templates" / "shared" / "final_review.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("逐问覆盖与主线", final_review)
        self.assertIn("Blocker / High 必须修改项", final_review)

        patch_plan = json.loads(
            (ROOT / "templates" / "shared" / "final_patch_plan.json").read_text(
                encoding="utf-8"
            )
        )
        contract = patch_plan["_patch_item_contract"]
        self.assertEqual(patch_plan["_schema_version"], "1.0")
        self.assertTrue({
            "id",
            "target",
            "severity",
            "problem",
            "evidence",
            "action",
            "acceptance_check",
            "status",
        }.issubset(set(contract["required_fields"])))
        self.assertTrue({"file", "anchor"}.issubset(set(contract["target_required_fields"])))

        handoff_template = (ROOT / "templates" / "shared" / "handoff.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("SubAgent 审查轨迹", handoff_template)
        self.assertIn("Rejected findings and reasons", handoff_template)
        self.assertIn("serial-<role>.md", protocol)
        self.assertNotIn("Conclusion: `<pass|conditional_pass|fail>`", template)

        stage_roles = {
            1: "2–4",
            3: "3–4",
            5: "3–5",
        }
        for stage, expected_fanout in stage_roles.items():
            path = next((ROOT / "references" / "workflow").glob(f"stage_{stage:02d}_*.md"))
            text = path.read_text(encoding="utf-8")
            self.assertIn("references/runtime/codex_subagents.md", text)
            self.assertIn(expected_fanout, text)
            self.assertIn(f"reviews/subagents/stage_{stage:02d}/*.md", text)

    def test_doctor_accepts_v4_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_workspace.initialize(workspace)
            checks = doctor.run_checks("cumcm", workspace=workspace)
            workspace_check = next(item for item in checks if item.name == "workspace-state")
            self.assertEqual(workspace_check.status, "pass", workspace_check.detail)


class LiteratureValidationTests(unittest.TestCase):
    def write_files(self, directory: Path, evidence_level: str, content_verified: bool):
        library = {
            "_schema_version": "1.0",
            "records": [{
                "id": "L1",
                "title": "示例",
                "authors": ["作者"],
                "year": 2025,
                "venue": "期刊",
                "language": "zh-CN",
                "source_type": "journal",
                "provider": "sciverse",
                "doc_id": "doc-1",
                "doi": None,
                "retrieved_at": "2026-08-03T00:00:00+00:00",
                "evidence_level": evidence_level,
                "metadata_verified": True,
                "content_verified": content_verified,
            }],
        }
        claim_map = {
            "_schema_version": "1.0",
            "claims": [{
                "id": "C1",
                "text": "某方法适用于该场景",
                "status": "supported",
                "support": [{"record_id": "L1", "locator": "摘要"}],
            }],
        }
        library_path = directory / "library.json"
        claim_path = directory / "claim_map.json"
        library_path.write_text(json.dumps(library, ensure_ascii=False), encoding="utf-8")
        claim_path.write_text(json.dumps(claim_map, ensure_ascii=False), encoding="utf-8")
        return library_path, claim_path

    def test_verified_abstract_can_support_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_files(Path(temp_dir), "abstract", True)
            self.assertEqual(validate_literature.validate(*paths), [])

    def test_metadata_only_cannot_support_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_files(Path(temp_dir), "metadata_only", False)
            errors = validate_literature.validate(*paths)
            self.assertTrue(any("metadata_only" in error for error in errors))


class PaperAssemblyTests(unittest.TestCase):
    def test_assembles_markdown_only_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            source = directory / "paper_draft.md"
            output = directory / "paper.md"
            source.write_text("# 论文\n", encoding="utf-8")
            assemble_paper.assemble(source, None, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "# 论文\n")
            with self.assertRaises(FileExistsError):
                assemble_paper.assemble(source, None, output)


if __name__ == "__main__":
    unittest.main()
