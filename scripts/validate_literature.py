#!/usr/bin/env python3
"""Validate literature metadata and claim-to-evidence links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EVIDENCE_LEVELS = {"metadata_only", "abstract", "full_text", "official_document"}
REQUIRED_RECORD_FIELDS = {
    "id", "title", "authors", "year", "venue", "language", "source_type",
    "provider", "retrieved_at", "evidence_level", "metadata_verified", "content_verified",
}


def load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根节点必须是对象: {path}")
    return value


def validate(library_path: Path, claim_map_path: Path) -> list[str]:
    errors: list[str] = []
    library = load_object(library_path)
    claim_map = load_object(claim_map_path)
    records = library.get("records")
    claims = claim_map.get("claims")
    if not isinstance(records, list):
        return ["library.records 必须是数组"]
    if not isinstance(claims, list):
        return ["claim_map.claims 必须是数组"]

    by_id: dict[str, dict[str, object]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"records[{index}] 必须是对象")
            continue
        missing = sorted(REQUIRED_RECORD_FIELDS - record.keys())
        if missing:
            errors.append(f"records[{index}] 缺少字段: {', '.join(missing)}")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"records[{index}].id 必须是非空字符串")
            continue
        if record_id in by_id:
            errors.append(f"重复文献 id: {record_id}")
        by_id[record_id] = record
        level = record.get("evidence_level")
        if level not in EVIDENCE_LEVELS:
            errors.append(f"{record_id} 的 evidence_level 非法: {level}")
        if not isinstance(record.get("authors"), list):
            errors.append(f"{record_id}.authors 必须是数组")
        if not isinstance(record.get("metadata_verified"), bool):
            errors.append(f"{record_id}.metadata_verified 必须是布尔值")
        if not isinstance(record.get("content_verified"), bool):
            errors.append(f"{record_id}.content_verified 必须是布尔值")
        if level == "metadata_only" and record.get("content_verified") is True:
            errors.append(f"{record_id} 仅有 metadata，不得标记 content_verified=true")
        if not record.get("doi") and not record.get("doc_id"):
            errors.append(f"{record_id} 至少需要 doi 或 doc_id")

    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] 必须是对象")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            errors.append(f"claims[{index}].id 必须是非空字符串")
            continue
        if claim_id in claim_ids:
            errors.append(f"重复 claim id: {claim_id}")
        claim_ids.add(claim_id)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append(f"{claim_id}.text 必须是非空字符串")
        support = claim.get("support")
        status = claim.get("status", "supported")
        if not isinstance(support, list):
            errors.append(f"{claim_id}.support 必须是数组")
            continue
        if status == "supported" and not support:
            errors.append(f"{claim_id} 标记为 supported 但没有证据")
        for support_index, link in enumerate(support):
            if not isinstance(link, dict):
                errors.append(f"{claim_id}.support[{support_index}] 必须是对象")
                continue
            record_id = link.get("record_id")
            record = by_id.get(record_id) if isinstance(record_id, str) else None
            if record is None:
                errors.append(f"{claim_id} 引用了不存在的文献: {record_id}")
                continue
            if record.get("evidence_level") == "metadata_only":
                errors.append(f"{claim_id} 不能由 metadata_only 文献 {record_id} 支撑")
            if record.get("content_verified") is not True:
                errors.append(f"{claim_id} 的文献 {record_id} 尚未核验内容")
            if not isinstance(link.get("locator"), str) or not link["locator"].strip():
                errors.append(f"{claim_id} 到 {record_id} 缺少页码/章节/摘要定位")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CUMCM literature evidence files.")
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--claim-map", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = validate(args.library, args.claim_map)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
