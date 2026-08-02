#!/usr/bin/env python3
"""Core regression tests for package integrity and deterministic workflow tools."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mathmodel_test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


doctor = load_script("doctor")
extract_diff = load_script("extract_diff")
render_ai_usage = load_script("render_ai_usage")
score_artifact = load_script("score_artifact")


def load_fixture(filename: str) -> dict:
    return json.loads(
        (ROOT / "tests" / "fixtures" / filename).read_text(encoding="utf-8")
    )


class PackageIntegrityTests(unittest.TestCase):
    def test_all_json_files_parse(self) -> None:
        json_paths = sorted(
            path for path in ROOT.rglob("*.json")
            if ".git" not in path.parts
        )

        self.assertTrue(json_paths)
        for path in json_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_all_stage_frontmatters_are_valid_yaml(self) -> None:
        stages = []
        paths = sorted((ROOT / "references").glob("stage_[0-9][0-9]_*.md"))
        self.assertEqual(len(paths), 10)

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                _, frontmatter, _ = text.split("---", 2)
                metadata = yaml.safe_load(frontmatter)
                self.assertIsInstance(metadata, dict)
                self.assertIsInstance(metadata.get("inputs"), list)
                self.assertIsInstance(metadata.get("outputs"), list)
                stages.append(metadata["stage"])

        self.assertEqual(stages, list(range(10)))

    def test_anti_pattern_counts_and_deferred_state(self) -> None:
        expected = {"cumcm": 42}
        pattern = re.compile(r"^###\s+([A-Z]\d+)\.\s", re.MULTILINE)

        for competition, count in expected.items():
            with self.subTest(competition=competition):
                text = (
                    ROOT / "competitions" / competition / "anti_patterns.md"
                ).read_text(encoding="utf-8")
                identifiers = pattern.findall(text)
                self.assertEqual(len(identifiers), count)
                self.assertEqual(len(set(identifiers)), count)

        decision_log = json.loads(
            (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                encoding="utf-8"
            )
        )
        declared = decision_log["stages"]["9"]["anti_patterns_check"]["total"]
        self.assertIsNone(declared)

    def test_effective_dimension_weights_only_use_valid_dimensions(self) -> None:
        table = json.loads(
            (ROOT / "config" / "dim_weights.json").read_text(encoding="utf-8")
        )
        for competition, competition_table in table.items():
            if competition.startswith("_") or not isinstance(competition_table, dict):
                continue
            for task_type in competition_table:
                if task_type.startswith("_"):
                    continue
                effective = score_artifact.load_dim_weights_table(competition, task_type)
                for stage, dimensions in effective.items():
                    with self.subTest(
                        competition=competition, task_type=task_type, stage=stage
                    ):
                        whitelist = score_artifact.load_dim_whitelist(
                            competition, int(stage)
                        )
                        configured = {
                            key for key in dimensions if not key.startswith("_")
                        }
                        self.assertLessEqual(configured, whitelist)


class ScoreArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.good = load_fixture("test_critique_good.json")

    def test_good_critique_validates(self) -> None:
        ok, message = score_artifact.validate_critique(self.good, 1, "cumcm")
        self.assertTrue(ok, message)

    def test_existing_competition_and_empirical_fixtures(self) -> None:
        empirical = score_artifact.load_empirical("nonexistent_competition")
        self.assertEqual(empirical, {})
        self.assertIn(
            "empirical 数据缺失",
            score_artifact.inject_evidence("abstract_chars", 700, empirical),
        )

        empirical_fixture = load_fixture("cumcm_empirical_inject.json")
        ok, message = score_artifact.validate_critique(
            empirical_fixture, 8, "cumcm"
        )
        self.assertTrue(ok, message)
        evidence = score_artifact.inject_evidence(
            "abstract_chars",
            empirical_fixture["evidence_metrics"]["abstract_chars"],
            score_artifact.load_empirical("cumcm"),
        )
        self.assertIn(empirical_fixture["_expected_output_contains"], evidence)
        self.assertIn("status=低于 p25", evidence)

    def test_bad_dimension_fixture_is_rejected(self) -> None:
        critique = load_fixture("test_critique_bad_keys.json")
        ok, message = score_artifact.validate_critique(critique, 1, "cumcm")
        self.assertFalse(ok)
        self.assertIn("dim key 不匹配", message)

    def test_inconsistent_or_invalid_score_inputs_are_rejected(self) -> None:
        cases = []

        wrong_stage = copy.deepcopy(self.good)
        wrong_stage["stage_id"] = 2
        cases.append(("stage", wrong_stage, "stage_id 不一致"))

        boolean_stage = copy.deepcopy(self.good)
        boolean_stage["stage_id"] = True
        cases.append(("boolean stage", boolean_stage, "stage_id 不一致"))

        wrong_minimum = copy.deepcopy(self.good)
        wrong_minimum["min_score"] = 8
        cases.append(("minimum", wrong_minimum, "min_score 与 scores 不一致"))

        boolean_minimum = copy.deepcopy(self.good)
        boolean_minimum["min_score"] = True
        cases.append(("boolean minimum", boolean_minimum, "min_score 与 scores 不一致"))

        wrong_mean = copy.deepcopy(self.good)
        wrong_mean["mean_score"] = 7.9
        cases.append(("mean", wrong_mean, "mean_score 与 scores 不一致"))

        invalid_iteration = copy.deepcopy(self.good)
        invalid_iteration["iteration"] = -1
        cases.append(("iteration", invalid_iteration, "iteration 必须是非负整数"))

        invalid_dimension_score = copy.deepcopy(self.good)
        invalid_dimension_score["scores"]["1_three_options_depth"]["score"] = True
        cases.append(("dimension score", invalid_dimension_score, "超出 [1,10]"))

        missing_evidence = copy.deepcopy(self.good)
        missing_evidence["scores"]["1_three_options_depth"].pop("evidence")
        cases.append(("evidence", missing_evidence, "evidence 必须是非空字符串"))

        malformed_issue = copy.deepcopy(self.good)
        malformed_issue["issues"] = [{
            "severity": "urgent",
            "where": "§1",
            "anti_pattern_id": None,
            "fix": "Repair the section.",
        }]
        cases.append(("issue", malformed_issue, "severity 必须是"))

        for name, critique, expected_message in cases:
            with self.subTest(name=name):
                ok, message = score_artifact.validate_critique(
                    critique, 1, "cumcm"
                )
                self.assertFalse(ok)
                self.assertIn(expected_message, message)

        ok, message = score_artifact.validate_critique([], 1, "cumcm")
        self.assertFalse(ok)
        self.assertIn("根节点", message)

    def test_cli_persists_recomputed_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            critique["verdict"] = "pass_early"
            critique_path.write_text(
                json.dumps(critique, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "score_artifact.py"),
                    "--stage",
                    "1",
                    "--critique",
                    str(critique_path),
                    "--decision-log",
                    str(decision_log_path),
                    "--competition",
                    "cumcm",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Actual: pass", result.stdout)
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["scores"]["1"][-1]["verdict"], "pass")
            self.assertEqual(persisted["iterations"]["1"], 1)
            self.assertEqual(list(temp_path.glob(".decision_log.json.*.tmp")), [])

    def test_cli_persists_carryover_at_iteration_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            for dim in critique["scores"].values():
                dim["score"] = 7
            critique.update({
                "iteration": 3,
                "min_score": 7,
                "mean_score": 7.0,
                "verdict": "refine",
            })
            critique_path.write_text(
                json.dumps(critique, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "score_artifact.py"),
                    "--stage",
                    "1",
                    "--critique",
                    str(critique_path),
                    "--decision-log",
                    str(decision_log_path),
                    "--competition",
                    "cumcm",
                    "--max-iter",
                    "3",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("下一步: carryover", result.stdout)
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["scores"]["1"][-1]["verdict"], "carryover"
            )

    def test_cli_fails_cleanly_on_malformed_json_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decision_log_path = temp_path / "decision_log.json"
            critique_path = temp_path / "critique.json"
            template = (
                ROOT / "templates" / "shared" / "decision_log.json"
            ).read_text(encoding="utf-8")

            cases = (
                (template, "[]", "critique 根节点必须是 object"),
                (template, "{", "critique 无法读取"),
                ("[]", json.dumps(self.good), "decision_log 根节点必须是 object"),
                ("{", json.dumps(self.good), "decision_log 无法读取"),
            )
            for decision_text, critique_text, expected in cases:
                with self.subTest(expected=expected):
                    decision_log_path.write_text(decision_text, encoding="utf-8")
                    critique_path.write_text(critique_text, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "score_artifact.py"),
                            "--stage",
                            "1",
                            "--critique",
                            str(critique_path),
                            "--decision-log",
                            str(decision_log_path),
                            "--competition",
                            "cumcm",
                        ],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(expected, result.stdout)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_decision_log_replace_is_atomic_and_in_same_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            critique = copy.deepcopy(self.good)
            original_replace = os.replace
            with mock.patch.object(
                score_artifact.os, "replace", wraps=original_replace
            ) as replace:
                score_artifact.update_decision_log(
                    1, critique, decision_log_path
                )

            replace.assert_called_once()
            source, destination = map(Path, replace.call_args.args)
            self.assertEqual(source.parent, decision_log_path.parent)
            self.assertEqual(destination, decision_log_path)
            self.assertFalse(source.exists())

    def test_atomic_json_rejects_non_finite_values_without_replacing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            original = '{"safe": true}\n'
            decision_log_path.write_text(original, encoding="utf-8")

            with self.assertRaises(ValueError):
                score_artifact._atomic_write_json(
                    decision_log_path, {"unsafe": math.nan}
                )

            self.assertEqual(
                decision_log_path.read_text(encoding="utf-8"), original
            )
            self.assertEqual(
                list(decision_log_path.parent.glob(".decision_log.json.*.tmp")), []
            )

    def test_stage5_aggregate_fixtures_and_persistence(self) -> None:
        passing = load_fixture("cumcm_stage5_per_qi.json")
        result = score_artifact.compute_stage5_verdict(
            passing["qi_results"], passing["qi_weights"]
        )
        expected = passing["_expected_output"]
        self.assertEqual(result["verdict"], expected["verdict"])
        self.assertEqual(result["review_qis"], expected["review_qis"])
        self.assertEqual(result["refine_qis"], expected["refine_qis"])
        self.assertEqual(result["weighted_min"], expected["weighted_min"])
        self.assertAlmostEqual(
            result["weighted_mean"], expected["weighted_mean_approx"], places=2
        )

        partial = load_fixture("cumcm_stage5_refine_partial.json")
        partial_result = score_artifact.compute_stage5_verdict(
            partial["qi_results"], partial["qi_weights"]
        )
        self.assertEqual(
            partial_result["verdict"], partial["_expected_output"]["verdict"]
        )
        self.assertEqual(
            partial_result["refine_qis"], partial["_expected_output"]["refine_qis"]
        )

        qi_results = passing["qi_results"][:2]
        result = score_artifact.compute_stage5_verdict(qi_results, None)
        self.assertEqual(result["qi_weights"], [1.0, 1.0])
        with tempfile.TemporaryDirectory() as temp:
            decision_log_path = Path(temp) / "decision_log.json"
            decision_log_path.write_text(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            score_artifact.update_stage5_aggregate(
                result, qi_results, None, decision_log_path
            )
            persisted = json.loads(decision_log_path.read_text(encoding="utf-8"))
            stage5 = persisted["stages"]["5"]
            self.assertEqual(stage5["qi_status"], result["qi_status"])
            self.assertEqual(stage5["aggregate"]["verdict"], result["verdict"])
            self.assertEqual(stage5["qi_weights"], [1.0, 1.0])

        with self.assertRaisesRegex(ValueError, "重复子问"):
            score_artifact.compute_stage5_verdict(
                [qi_results[0], dict(qi_results[0])]
            )

    def test_stage5_aggregate_rejects_inconsistent_or_non_finite_input(self) -> None:
        good = [
            {"qi": "Q1", "min": 7, "mean": 8.0, "issues": []},
            {"qi": "Q2", "min": 8, "mean": 8.4, "issues": []},
        ]
        cases = [
            ([], None, "至少包含一个"),
            ([{"qi": "Q1", "min": 9, "mean": 8}], None, "不能大于"),
            (good, [1.0], "长度"),
            (good, [1.0, math.nan], "有限正数"),
            (good, [1.0, math.inf], "有限正数"),
        ]
        inconsistent_scores = copy.deepcopy(good)
        inconsistent_scores[0]["scores"] = {
            f"dim_{index}": {"score": score}
            for index, score in enumerate((7, 8, 8, 8, 8), 1)
        }
        inconsistent_scores[0]["mean"] = 9.0
        cases.append((inconsistent_scores, None, "mean 与 scores 不一致"))

        for qi_results, qi_weights, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    score_artifact.compute_stage5_verdict(
                        qi_results, qi_weights
                    )


class QiCritiqueFileTests(unittest.TestCase):
    """Stage 5 per-Qi 独立文件写入与聚合 (multi-Agent 并行安全)."""

    def _critique(self, qi_id: str, min_score: int = 8, mean: float = 8.0,
                  has_high_issue: bool = False) -> dict:
        issues = []
        if has_high_issue:
            issues = [{"severity": "high", "where": "Q1", "fix": "x"}]
        return {
            "qi_id": qi_id,
            "iteration": 0,
            "scores": {f"dim_{i}": {"score": 8} for i in range(1, 6)},
            "min": min_score,
            "mean": mean,
            "verdict": "pass",
            "issues": issues,
        }

    def test_write_qi_critique_isolated_per_qi(self) -> None:
        """每个 Qi 写独立文件, 并发写不同 Qi 互不覆盖 (方案1 核心)."""
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            p1 = score_artifact.write_qi_critique(self._critique("Q1"), state_dir)
            p2 = score_artifact.write_qi_critique(self._critique("Q2"), state_dir)
            self.assertEqual(p1.name, "qi_Q1.json")
            self.assertEqual(p2.name, "qi_Q2.json")
            self.assertNotEqual(p1, p2)
            # 两个文件都在, 内容各自完整
            self.assertEqual(json.loads(p1.read_text(encoding="utf-8"))["qi_id"], "Q1")
            self.assertEqual(json.loads(p2.read_text(encoding="utf-8"))["qi_id"], "Q2")

    def test_write_qi_critique_same_qi_overwrites_in_place(self) -> None:
        """同一 Qi 重复写是原地替换, 不产生残留临时文件. 原子性验证."""
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            p = score_artifact.write_qi_critique(self._critique("Q1"), state_dir)
            first = p.read_text(encoding="utf-8")
            # 第二次写 (迭代) 覆盖同一路径
            score_artifact.write_qi_critique(self._critique("Q1", min_score=9), state_dir)
            second = p.read_text(encoding="utf-8")
            self.assertNotEqual(first, second)
            self.assertEqual(json.loads(second)["min"], 9)
            # 无残留临时文件
            self.assertEqual(list(state_dir.rglob("*.tmp")), [])

    def test_load_qi_critiques_dir_aggregates_sorted(self) -> None:
        """聚合读取目录下所有 qi 文件, 按 qi_id 排序, 输出可直接喂 verdict."""
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            score_artifact.write_qi_critique(self._critique("Q1"), state_dir)
            score_artifact.write_qi_critique(self._critique("Q5"), state_dir)
            score_artifact.write_qi_critique(self._critique("Q3"), state_dir)
            items = score_artifact.load_qi_critiques_dir(
                state_dir / score_artifact.QI_CRITIQUES_DIR
            )
            self.assertEqual([i["qi"] for i in items], ["Q1", "Q3", "Q5"])
            self.assertTrue(all("scores" in i and "issues" in i for i in items))
            # 可直接喂 compute_stage5_verdict
            result = score_artifact.compute_stage5_verdict(items, None)
            self.assertEqual(result["verdict"], "pass")

    def test_load_qi_critiques_dir_rejects_missing_qi_id(self) -> None:
        """聚合时发现缺 qi_id 的文件必须报错, 不静默跳过."""
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            bad = state_dir / score_artifact.QI_CRITIQUES_DIR / "qi_X.json"
            bad.parent.mkdir(parents=True)
            bad.write_text(json.dumps({"min": 8}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "缺少 qi_id"):
                score_artifact.load_qi_critiques_dir(
                    state_dir / score_artifact.QI_CRITIQUES_DIR
                )


class ExtractDiffTests(unittest.TestCase):
    def test_apply_mode_does_not_require_critique(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            artifact = temp_path / "artifact.md"
            patch = temp_path / "patch.txt"
            artifact.write_text(
                "# Paper\n\nIntro.\n\n## Model\n\nOld text.\n", encoding="utf-8"
            )
            patch.write_text(
                "<<< SECTION_PATCH issue_0\n"
                "## Model\n\nNew text.\n"
                ">>>\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_diff.py"),
                    "--artifact",
                    str(artifact),
                    "--mode",
                    "section",
                    "--apply",
                    str(patch),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("## Model\n\nNew text.", result.stdout)
            self.assertNotIn("Old text.", result.stdout)

    def test_unknown_patch_heading_fails(self) -> None:
        artifact = "# Paper\n\nText.\n"
        patch = "<<< SECTION_PATCH issue_0\n## Missing\n\nNew.\n>>>"
        with self.assertRaisesRegex(ValueError, "无法定位"):
            extract_diff.apply_section_patches(artifact, patch)

    def test_duplicate_artifact_heading_fails_as_ambiguous(self) -> None:
        artifact = "## Model\n\nOne.\n\n## Model\n\nTwo.\n"
        patch = "<<< SECTION_PATCH issue_0\n## Model\n\nNew.\n>>>"
        with self.assertRaisesRegex(ValueError, "重复"):
            extract_diff.apply_section_patches(artifact, patch)


class DoctorTests(unittest.TestCase):
    def test_all_competition_preflights_pass(self) -> None:
        for competition in doctor.COMPETITIONS:
            with self.subTest(competition=competition):
                checks = doctor.run_checks(competition)
                failures = [
                    f"{item.name}: {item.detail}"
                    for item in checks
                    if item.status == "fail"
                ]
                self.assertEqual(failures, [])

    def test_workspace_state_requires_v31_and_matching_competition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            state_path = workspace / "state" / "decision_log.json"
            state_path.parent.mkdir()
            state = json.loads(
                (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                    encoding="utf-8"
                )
            )
            state["competition"] = "cumcm"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            checks = doctor.run_checks("cumcm", workspace=workspace)
            workspace_check = next(
                item for item in checks if item.name == "workspace-state"
            )
            self.assertEqual(workspace_check.status, "pass")

            mismatch = doctor.run_checks("other_competition", workspace=workspace)
            mismatch_check = next(
                item for item in mismatch if item.name == "workspace-state"
            )
            self.assertEqual(mismatch_check.status, "fail")

            state["current_stage"] = True
            state_path.write_text(json.dumps(state), encoding="utf-8")
            boolean_stage = doctor.run_checks("cumcm", workspace=workspace)
            boolean_check = next(
                item for item in boolean_stage if item.name == "workspace-state"
            )
            self.assertEqual(boolean_check.status, "fail")


class DecisionLogSchemaTests(unittest.TestCase):
    def test_dynamic_counts_and_unobservable_token_usage_default_to_null(self) -> None:
        state = json.loads(
            (ROOT / "templates" / "shared" / "decision_log.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsNone(state["budget"]["tokens_used"])
        self.assertIsNone(state["budget"]["tokens_cap"])
        self.assertIsNone(state["stages"]["9"]["anti_patterns_check"]["total"])
        self.assertIn("paper_metadata", state)


if __name__ == "__main__":
    unittest.main()
