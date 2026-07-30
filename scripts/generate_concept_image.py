#!/usr/bin/env python3
"""通过 PackyAPI 调用 gpt-image-2 生成学术概念图。

环境变量:
    PACKYAPI_TOKEN: PackyAPI Bearer Token (必需)
    PACKYAPI_BASE_URL: 默认 https://www.packyai.ai

用法:
    python generate_concept_image.py \
        --prompt "学术论文插图，系统架构图，展示..." \
        --output figures/system_arch.png \
        --size 1536x1024 \
        --quality high

    # 批量生成
    python generate_concept_image.py --batch prompts.json --output-dir figures/
"""

import argparse
import base64
import json
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import httpx

BASE_URL = os.environ.get("PACKYAPI_BASE_URL", "https://www.packyapi.com")
TOKEN = os.environ.get("PACKYAPI_TOKEN", "")

# 学术概念图 prompt 前缀 — 确保风格统一、可黑白印刷
ACADEMIC_PREFIX = (
    "Academic scientific illustration. Clean vector-like style. "
    "White background. Thin black lines. Chinese text labels where needed. "
    "Designed for black-and-white printing. No color gradients. "
    "Professional, minimal, suitable for a mathematical modeling competition paper."
)


def generate_image(
    prompt: str,
    output_path: str,
    size: str = "1536x1024",
    quality: str = "high",
    output_format: str = "png",
    academic_style: bool = True,
) -> dict:
    """调用 PackyAPI /v1/images/generations 生成图片。

    Args:
        prompt: 图片描述
        output_path: 输出文件路径
        size: 图片尺寸 (1024x1024 / 1536x1024 / 1024x1536 / 1536x864 / 3840x2160 / auto)
        quality: 质量 (low / medium / high / auto)
        output_format: 输出格式 (png / jpeg)
        academic_style: 是否添加学术风格前缀

    Returns:
        dict: {"success": bool, "path": str, "url": str | None, "error": str | None}
    """
    if not TOKEN:
        return {"success": False, "path": output_path, "url": None, "error": "PACKYAPI_TOKEN 未设置"}

    full_prompt = f"{ACADEMIC_PREFIX}\n\n具体内容: {prompt}" if academic_style else prompt

    payload = {
        "model": "gpt-image-2",
        "prompt": full_prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "output_format": output_format,
    }

    try:
        resp = httpx.post(
            f"{BASE_URL}/v1/images/generations",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        # 解析 b64_json 响应
        image_data = None
        if "data" in data and len(data["data"]) > 0:
            item = data["data"][0]
            if "b64_json" in item:
                image_data = base64.b64decode(item["b64_json"])
            elif "url" in item:
                # 如果返回的是 URL，下载图片
                img_resp = httpx.get(item["url"], timeout=60)
                img_resp.raise_for_status()
                image_data = img_resp.content

        if image_data:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(image_data)
            return {"success": True, "path": output_path, "url": None, "error": None}
        else:
            return {"success": False, "path": output_path, "url": None, "error": f"响应中无图片数据: {data}"}

    except httpx.HTTPError as e:
        detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                detail += f" | body: {e.response.text[:300]}"
            except Exception:
                pass
        return {"success": False, "path": output_path, "url": None, "error": detail}
    except Exception as e:
        return {"success": False, "path": output_path, "url": None, "error": str(e)}


def batch_generate(prompts_file: str, output_dir: str, **kwargs) -> list[dict]:
    """批量生成图片。

    prompts.json 格式:
    [
        {"prompt": "...", "filename": "fig1.png", "size": "1536x1024"},
        ...
    ]
    """
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    results = []
    for item in prompts:
        output_path = str(Path(output_dir) / item["filename"])
        result = generate_image(
            prompt=item["prompt"],
            output_path=output_path,
            size=item.get("size", kwargs.get("size", "1536x1024")),
            quality=item.get("quality", kwargs.get("quality", "high")),
            output_format=item.get("output_format", kwargs.get("output_format", "png")),
            academic_style=item.get("academic_style", True),
        )
        results.append(result)
        status = "[OK]" if result["success"] else "[FAIL]"
        print(f"{status} {item['filename']}: {result.get('error', 'OK')}")

    return results


def main():
    parser = argparse.ArgumentParser(description="gpt-image-2 学术概念图生成")
    parser.add_argument("--prompt", help="图片描述 prompt")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--size", default="1536x1024", help="图片尺寸 (默认 1536x1024)")
    parser.add_argument("--quality", default="high", help="质量: low/medium/high/auto (默认 high)")
    parser.add_argument("--format", default="png", help="输出格式: png/jpeg (默认 png)")
    parser.add_argument("--no-academic", action="store_true", help="不添加学术风格前缀")
    parser.add_argument("--batch", help="批量生成: prompts.json 文件路径")
    parser.add_argument("--output-dir", default="figures/", help="批量生成输出目录 (默认 figures/)")

    args = parser.parse_args()

    if args.batch:
        results = batch_generate(
            prompts_file=args.batch,
            output_dir=args.output_dir,
            size=args.size,
            quality=args.quality,
            output_format=args.format,
        )
        success_count = sum(1 for r in results if r["success"])
        print(f"\n完成: {success_count}/{len(results)} 张图生成成功")
        if success_count < len(results):
            sys.exit(1)
    elif args.prompt and args.output:
        result = generate_image(
            prompt=args.prompt,
            output_path=args.output,
            size=args.size,
            quality=args.quality,
            output_format=args.format,
            academic_style=not args.no_academic,
        )
        if result["success"]:
            print(f"[OK] 图片已保存: {result['path']}")
        else:
            print(f"[FAIL] 生成失败: {result['error']}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
