#!/usr/bin/env python3
"""Assemble the final Markdown paper; deliberately does not create DOCX or PDF."""

from __future__ import annotations

import argparse
from pathlib import Path


def assemble(source: Path | None, parts_dir: Path | None, output: Path, force: bool = False) -> Path:
    if (source is None) == (parts_dir is None):
        raise ValueError("必须且只能提供 --source 或 --parts-dir")
    if output.exists() and not force:
        raise FileExistsError(f"输出已存在，使用 --force 才能覆盖: {output}")
    if source is not None:
        text = source.read_text(encoding="utf-8").rstrip() + "\n"
    else:
        parts = sorted(path for path in parts_dir.glob("*.md") if path.is_file())
        if not parts:
            raise ValueError(f"未找到 Markdown 分节: {parts_dir}")
        text = "\n\n".join(part.read_text(encoding="utf-8").strip() for part in parts) + "\n"
    if not text.strip():
        raise ValueError("论文内容为空")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble paper.md only.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", type=Path)
    group.add_argument("--parts-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("paper.md"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        output = assemble(args.source, args.parts_dir, args.output, args.force)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
