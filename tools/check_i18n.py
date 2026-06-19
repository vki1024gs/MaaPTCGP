#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DISPLAY_FIELDS = {
    "label",
    "description",
    "contact",
    "details",
    "summary",
    "focus",
}
PATH_FIELDS = {
    "icon",
    "license",
    "welcome",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.loads(strip_jsonc_comments(f.read()))


def strip_jsonc_comments(text: str) -> str:
    result = []
    state = 0
    i = 0
    while i < len(text):
        char = text[i]
        if state == 0:
            if char == '"':
                result.append(char)
                state = 1
                i += 1
            elif i + 1 < len(text) and text[i : i + 2] == "//":
                while i < len(text) and text[i] != "\n":
                    i += 1
                if i < len(text):
                    result.append("\n")
                    i += 1
            elif i + 1 < len(text) and text[i : i + 2] == "/*":
                i += 2
                while i + 1 < len(text) and text[i : i + 2] != "*/":
                    if text[i] == "\n":
                        result.append("\n")
                    i += 1
                i += 2
            else:
                result.append(char)
                i += 1
        elif state == 1:
            result.append(char)
            if char == "\\":
                state = 2
            elif char == '"':
                state = 0
            i += 1
        else:
            result.append(char)
            state = 1
            i += 1
    return "".join(result)


def is_i18n(value: str) -> bool:
    return value.startswith("$")


def is_path_like(value: str) -> bool:
    return (
        "/" in value
        or value.startswith(".")
        or value.endswith((".md", ".png", ".ico", ".jpg", ".jpeg", ".webp", ".svg"))
    )


def walk(value, path, file_path, refs, hardcoded):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + [key]
            if isinstance(child, str):
                if key in DISPLAY_FIELDS:
                    if is_i18n(child):
                        refs.append((file_path, child_path, child[1:]))
                    elif key == "focus":
                        pass
                    else:
                        hardcoded.append((file_path, child_path, child))
                elif key in PATH_FIELDS and is_i18n(child):
                    refs.append((file_path, child_path, child[1:]))
            walk(child, child_path, file_path, refs, hardcoded)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, path + [str(index)], file_path, refs, hardcoded)


def collect_files():
    files = [ASSETS / "interface.json"]
    task_dir = ASSETS / "tasks"
    if task_dir.exists():
        files.extend(sorted(task_dir.rglob("*.json")))
    return files


def main():
    interface = load_json(ASSETS / "interface.json")
    language_files = {
        lang: ASSETS / path
        for lang, path in interface.get("languages", {}).items()
    }

    refs = []
    hardcoded = []
    for file_path in collect_files():
        walk(load_json(file_path), [], file_path, refs, hardcoded)

    ok = True
    if hardcoded:
        ok = False
        print("Hardcoded user-facing display fields found:")
        for file_path, json_path, value in hardcoded:
            rel = file_path.relative_to(ROOT)
            print(f"  {rel}:{'.'.join(json_path)} = {value!r}")

    ref_keys = {key for _, _, key in refs}
    for lang, file_path in language_files.items():
        if not file_path.exists():
            ok = False
            print(f"Missing language file for {lang}: {file_path.relative_to(ROOT)}")
            continue
        data = load_json(file_path)
        missing = sorted(ref_keys - set(data))
        if missing:
            ok = False
            print(f"Missing {lang} translations:")
            for key in missing:
                print(f"  {key}")

        for key, value in data.items():
            if key.endswith(".file") and isinstance(value, str):
                target = ASSETS / value
                if not is_path_like(value) or not target.exists():
                    ok = False
                    print(
                        f"Invalid {lang} file reference {key}: "
                        f"{value!r}"
                    )

    for key in PATH_FIELDS:
        value = interface.get(key)
        if isinstance(value, str) and not is_i18n(value):
            candidates = [ASSETS / value, ROOT / value]
            if not any(path.exists() for path in candidates):
                ok = False
                print(f"Missing interface path {key}: {value!r}")

    if ok:
        print(
            f"i18n check passed: {len(ref_keys)} keys, "
            f"{len(language_files)} languages"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
