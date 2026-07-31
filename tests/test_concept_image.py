#!/usr/bin/env python3
"""Unit tests for scripts/generate_concept_image.py (gpt-image-2 via PackyAPI)."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(token: str = "TEST_TOKEN"):
    """Load the script as a module with a controlled PACKYAPI_TOKEN."""
    path = ROOT / "scripts" / "generate_concept_image.py"
    spec = importlib.util.spec_from_file_location(
        "mathmodel_concept_image", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with mock.patch.dict("os.environ", {"PACKYAPI_TOKEN": token}, clear=False):
        spec.loader.exec_module(module)
    return module


class TokenGuardTests(unittest.TestCase):
    def test_missing_token_fails_fast(self) -> None:
        module = load_module(token="")
        result = module.generate_image(
            prompt="test", output_path=str(Path("figures") / "x.png")
        )
        self.assertFalse(result["success"])
        self.assertIn("PACKYAPI_TOKEN", result["error"])


class GenerateImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_b64_response_is_decoded_and_written(self) -> None:
        png_bytes = b"\x89PNG\r\n\x1a\nfake-image"
        fake_response = mock.Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(png_bytes).decode("ascii")}]
        }

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fig" / "arch.png"
            with mock.patch.object(self.module.httpx, "post", return_value=fake_response):
                result = self.module.generate_image(
                    prompt="architecture", output_path=str(output)
                )

            self.assertTrue(result["success"])
            self.assertEqual(output.read_bytes(), png_bytes)

    def test_url_response_is_downloaded(self) -> None:
        png_bytes = b"\x89PNG\r\n\x1a\nfake-image"
        gen_response = mock.Mock()
        gen_response.raise_for_status.return_value = None
        gen_response.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
        img_response = mock.Mock()
        img_response.raise_for_status.return_value = None
        img_response.content = png_bytes

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fig.png"
            with mock.patch.object(self.module.httpx, "post", return_value=gen_response), \
                 mock.patch.object(self.module.httpx, "get", return_value=img_response):
                result = self.module.generate_image(
                    prompt="architecture", output_path=str(output)
                )

            self.assertTrue(result["success"])
            self.assertEqual(output.read_bytes(), png_bytes)

    def test_http_error_is_reported_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fig.png"
            with mock.patch.object(
                self.module.httpx,
                "post",
                side_effect=self.module.httpx.HTTPStatusError(
                    "500 Server Error", request=mock.Mock(), response=mock.Mock()
                ),
            ):
                result = self.module.generate_image(
                    prompt="x", output_path=str(output)
                )

            self.assertFalse(result["success"])
            self.assertIn("500", result["error"])

    def test_missing_image_data_reports_parse_failure(self) -> None:
        fake_response = mock.Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {"data": []}

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fig.png"
            with mock.patch.object(self.module.httpx, "post", return_value=fake_response):
                result = self.module.generate_image(
                    prompt="x", output_path=str(output)
                )

            self.assertFalse(result["success"])
            self.assertIn("无图片数据", result["error"])

    def test_academic_prefix_applied_only_when_enabled(self) -> None:
        fake_response = mock.Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode("ascii")}]
        }

        with mock.patch.object(self.module.httpx, "post", return_value=fake_response) as post:
            with tempfile.TemporaryDirectory() as temp:
                self.module.generate_image("plain", str(Path(temp) / "a.png"))
                self.module.generate_image(
                    "plain", str(Path(temp) / "b.png"), academic_style=False
                )

        self.assertIn(self.module.ACADEMIC_PREFIX, post.call_args_list[0].kwargs["json"]["prompt"])
        self.assertNotIn(
            self.module.ACADEMIC_PREFIX, post.call_args_list[1].kwargs["json"]["prompt"]
        )


class BatchGenerateTests(unittest.TestCase):
    def test_batch_passes_per_item_options_and_returns_results(self) -> None:
        module = load_module()
        fake_response = mock.Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode("ascii")}]
        }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prompts_file = root / "prompts.json"
            prompts_file.write_text(
                json.dumps(
                    [
                        {"prompt": "a", "filename": "a.png", "size": "1024x1024"},
                        {"prompt": "b", "filename": "b.png"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with mock.patch.object(module.httpx, "post", return_value=fake_response) as post:
                results = module.batch_generate(
                    str(prompts_file), str(root / "figures"), size="1536x1024"
                )

            self.assertEqual(len(results), 2)
            self.assertTrue(all(r["success"] for r in results))
            self.assertTrue((root / "figures" / "a.png").exists())
            self.assertTrue((root / "figures" / "b.png").exists())
            # per-item size override wins; default falls back to batch kwarg
            self.assertEqual(post.call_args_list[0].kwargs["json"]["size"], "1024x1024")
            self.assertEqual(post.call_args_list[1].kwargs["json"]["size"], "1536x1024")

    def test_batch_missing_prompts_file_fails_cleanly(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                module.batch_generate(
                    str(Path(temp) / "nope.json"), str(Path(temp) / "figures")
                )


if __name__ == "__main__":
    unittest.main()
