#!/usr/bin/env python3
"""
Strip private/editor-only fields from public pipeline resources.

This tool is for the sanitized public repository only. Do not run it in the
private development repository: MPE metadata and verbose desc fields are useful
editor/development state there.

Default mode is check-only. Use --write in the public repository to remove
private/editor-only fields in place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEV_REPO_MARKERS = (
    "AGENTS.md",
    ".codex",
    ".claude",
    "dev-tools",
    "dev-images",
)


def is_private_pipeline_key(key: str) -> bool:
    return key == "desc" or key.startswith("$__mpe")


def strip_private_fields(value: Any, path: str = "") -> tuple[Any, list[str]]:
    removed: list[str] = []

    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            item_path = f"{path}/{key}" if path else key
            if is_private_pipeline_key(key):
                removed.append(item_path)
                continue
            clean_item, item_removed = strip_private_fields(item, item_path)
            clean[key] = clean_item
            removed.extend(item_removed)
        return clean, removed

    if isinstance(value, list):
        clean_list = []
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            clean_item, item_removed = strip_private_fields(item, item_path)
            clean_list.append(clean_item)
            removed.extend(item_removed)
        return clean_list, removed

    return value, removed


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def iter_json_files(resource_dir: Path) -> list[Path]:
    if not resource_dir.exists():
        raise SystemExit(f"resource directory does not exist: {resource_dir}")
    return sorted(path for path in resource_dir.rglob("*.json") if path.is_file())


def assert_public_repo(root: Path, allow_dev_repo: bool) -> None:
    if allow_dev_repo:
        return

    found = [marker for marker in DEV_REPO_MARKERS if (root / marker).exists()]
    if not found:
        return

    markers = ", ".join(found)
    raise SystemExit(
        "refusing to strip private/editor-only pipeline fields in a development repository "
        f"({markers} found). This tool is intended for the public sanitized "
        "repository only."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or remove public-only stripped pipeline fields from JSON files."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to operate on (default: current directory).",
    )
    parser.add_argument(
        "--resource-dir",
        type=Path,
        default=Path("assets/resource/pipeline"),
        help="Pipeline resource directory relative to --root.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite files in place. Without this flag the tool only checks.",
    )
    parser.add_argument(
        "--allow-dev-repo",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    root = args.root.resolve()
    assert_public_repo(root, args.allow_dev_repo)

    resource_dir = args.resource_dir
    if not resource_dir.is_absolute():
        resource_dir = root / resource_dir

    changed: dict[Path, list[str]] = {}
    for path in iter_json_files(resource_dir):
        data = load_json(path)
        clean, removed = strip_private_fields(data)
        if removed:
            changed[path] = removed
            if args.write:
                write_json(path, clean)

    if not changed:
        print("No private/editor-only pipeline fields found.")
        return 0

    mode = "Removed" if args.write else "Found"
    print(f"{mode} private/editor-only pipeline fields in {len(changed)} file(s):")
    for path, removed in changed.items():
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        print(f"- {rel}")
        for item in removed:
            print(f"  - {item}")

    if args.write:
        return 0

    print("\nRun again with --write in the public repository to remove them.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
