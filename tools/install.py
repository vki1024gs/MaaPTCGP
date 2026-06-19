from pathlib import Path

import json
import re
import shutil
import stat
import sys


working_dir = Path(__file__).parent.parent.resolve()
install_path = working_dir / "install"
install_cli_path = working_dir / "install-cli"
version = sys.argv[1] if len(sys.argv) > 1 else "v0.0.1"

if len(sys.argv) < 4:
    print("Usage: python install.py <version> <os> <arch>")
    print("Example: python install.py v1.0.0 macos aarch64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]

SUPPORTED_TARGETS = {
    ("win", "x86_64"),
    ("win", "aarch64"),
    ("macos", "x86_64"),
    ("macos", "aarch64"),
    ("linux", "x86_64"),
}

COPY_IGNORE = shutil.ignore_patterns(
    ".DS_Store",
    ".archives",
    "*.bak",
    "*.tmp",
    "__pycache__",
)


def require_supported_target():
    if (os_name, arch) not in SUPPORTED_TARGETS:
        print("Unsupported MXU target.")
        print("available os/arch:")
        for target_os, target_arch in sorted(SUPPORTED_TARGETS):
            print(f"  {target_os} {target_arch}")
        sys.exit(1)


def clean_install():
    if install_path.exists():
        shutil.rmtree(install_path)
    install_path.mkdir(parents=True)


def clean_install_cli():
    if install_cli_path.exists():
        shutil.rmtree(install_cli_path)
    install_cli_path.mkdir(parents=True)


def copytree(src: Path, dst: Path, *, ignore=COPY_IGNORE):
    if not src.exists():
        print(f"Missing required path: {src}")
        sys.exit(1)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def install_mxu_shell():
    mxu_dir = working_dir / "MXU"
    if not mxu_dir.exists():
        print('Missing MXU — please download it from https://github.com/MistEO/MXU/releases')
        print('Then extract and place the contents into a "MXU" folder next to this script.')
        print()
        print('缺少 MXU — 请从 https://github.com/MistEO/MXU/releases 下载')
        print('解压后将内容放到脚本同级目录下的 "MXU" 文件夹中。')
        sys.exit(1)

    for item in mxu_dir.iterdir():
        if item.name.startswith("."):
            continue
        dst = install_path / item.name
        if item.is_dir():
            copytree(item, dst)
        elif item.is_file():
            shutil.copy2(item, dst)

    if os_name == "win":
        candidates = ["mxu.exe", "MXU.exe"]
        target_name = "MaaPTCGP.exe"
    else:
        candidates = ["mxu", "MXU"]
        target_name = "MaaPTCGP"

    executable = None
    for candidate in candidates:
        path = install_path / candidate
        if path.exists():
            executable = path
            break

    if executable is None:
        print("MXU executable was not found after copying MXU files.")
        print(f"Expected one of: {', '.join(candidates)}")
        sys.exit(1)

    target = install_path / target_name
    if executable != target:
        if target.exists():
            target.unlink()
        executable.rename(target)

    if os_name != "win":
        mode = target.stat().st_mode
        target.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_maafw_for_mxu():
    deps_bin = working_dir / "deps" / "bin"
    agent_binary = working_dir / "deps" / "share" / "MaaAgentBinary"

    if not deps_bin.exists():
        print('Missing MaaFramework — please download it from https://github.com/MaaXYZ/MaaFramework/releases')
        print('Then extract and place the contents into a "deps" folder next to this script.')
        print()
        print('缺少 MaaFramework — 请从 https://github.com/MaaXYZ/MaaFramework/releases 下载')
        print('解压后将内容放到脚本同级目录下的 "deps" 文件夹中。')
        sys.exit(1)

    copytree(
        deps_bin,
        install_path / "maafw",
        ignore=shutil.ignore_patterns(
            ".DS_Store",
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
            "*.node",
            "*MaaPiCli*",
        ),
    )

    if agent_binary.exists():
        copytree(agent_binary, install_path / "maafw" / "MaaAgentBinary")


def install_maafw_for_cli():
    deps_bin = working_dir / "deps" / "bin"

    if not deps_bin.exists():
        print('Missing MaaFramework — please download it from https://github.com/MaaXYZ/MaaFramework/releases')
        print('Then extract and place the contents into a "deps" folder next to this script.')
        sys.exit(1)

    copytree(
        deps_bin,
        install_cli_path,
        ignore=shutil.ignore_patterns(
            ".DS_Store",
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
        ),
    )

    executable = install_cli_path / maa_pi_cli_name()
    if executable.exists() and os_name != "win":
        mode = executable.stat().st_mode
        executable.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_resource():
    copytree(working_dir / "assets" / "resource", install_path / "resource")
    install_ocr_model()
    copytree(working_dir / "assets" / "tasks", install_path / "tasks")
    copytree(working_dir / "assets" / "locales", install_path / "locales")

    shutil.copy2(working_dir / "assets" / "interface.json", install_path)
    normalize_release_interface()
    normalize_release_tasks()


def install_cli_resource():
    copytree(working_dir / "assets" / "resource", install_cli_path / "resource")
    install_cli_ocr_model()
    copytree(working_dir / "assets" / "tasks", install_cli_path / "tasks")
    copytree(working_dir / "assets" / "locales", install_cli_path / "locales")

    shutil.copy2(working_dir / "assets" / "interface.json", install_cli_path)
    normalize_cli_interface()
    normalize_cli_tasks()
    install_cli_config()


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


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")


def is_dev_install_version():
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if not match:
        return False
    return int(match.group(1)) < 1


def prefer_dev_resource(resources):
    return sorted(resources, key=lambda item: 0 if item.get("name") == "Dev" else 1)


def normalize_release_interface():
    interface_path = install_path / "interface.json"
    interface = load_json(interface_path)

    interface["version"] = version
    if is_dev_install_version():
        interface["resource"] = prefer_dev_resource(interface.get("resource", []))
    else:
        interface["resource"] = [
            resource
            for resource in interface.get("resource", [])
            if resource.get("name") != "Dev"
        ]
        resource_names = {item.get("name") for item in interface.get("resource", [])}
        if "Default" not in resource_names:
            print('Install normalization failed. Release interface must include "Default" resource.')
            sys.exit(1)

    dump_json(interface_path, interface)


def normalize_release_tasks():
    for task_file in (install_path / "tasks").rglob("*.json"):
        data = load_json(task_file)
        if is_dev_install_version():
            prefer_dev_task_resources(data)
        else:
            strip_dev_resource(data)
        dump_json(task_file, data)


def normalize_cli_interface():
    interface_path = install_cli_path / "interface.json"
    interface = load_json(interface_path)
    interface["version"] = version
    interface["resource"] = prefer_dev_resource(interface.get("resource", []))
    dump_json(interface_path, interface)


def normalize_cli_tasks():
    for task_file in (install_cli_path / "tasks").rglob("*.json"):
        data = load_json(task_file)
        prefer_dev_task_resources(data)
        dump_json(task_file, data)


def prefer_dev_task_resources(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "resource" and isinstance(child, list) and "Dev" in child:
                value[key] = ["Dev", *[item for item in child if item != "Dev"]]
            else:
                prefer_dev_task_resources(child)
    elif isinstance(value, list):
        for child in value:
            prefer_dev_task_resources(child)


def strip_dev_resource(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "resource" and isinstance(child, list):
                value[key] = [item for item in child if item != "Dev"]
            else:
                strip_dev_resource(child)
    elif isinstance(value, list):
        for child in value:
            strip_dev_resource(child)


def install_ocr_model():
    source = working_dir / "assets" / "MaaCommonAssets" / "OCR" / "ppocr_v5" / "zh_cn"
    target = install_path / "resource" / "model" / "ocr"
    if target.exists():
        return
    copytree(source, target)


def install_cli_ocr_model():
    source = working_dir / "assets" / "MaaCommonAssets" / "OCR" / "ppocr_v5" / "zh_cn"
    target = install_cli_path / "resource" / "model" / "ocr"
    if target.exists():
        return
    copytree(source, target)


def install_cli_config():
    config_path = install_cli_path / "config"
    config_path.mkdir(parents=True, exist_ok=True)

    maa_pi_config = {
        "adb": {
            "adb_path": "/Applications/BlueStacks.app/Contents/MacOS/hd-adb",
            "address": "127.0.0.1:5565",
            "name": "127.0.0.1:5565-BlueStacks",
        },
        "controller": {
            "name": "ADB",
        },
        "controller_option": [],
        "gamepad": {
            "_placeholder": 0,
            "gamepad_type": "",
        },
        "global_option": [],
        "macos": {
            "input": "",
            "screencap": "",
            "title": "",
            "window_id": 0,
        },
        "playcover": {
            "address": "",
            "uuid": "",
        },
        "resource": "Dev",
        "resource_option": [],
        "task": [
            {"name": "StartToHome", "option": []},
            {"name": "ClaimGiftBoxMail", "option": []},
            {
                "name": "Pack",
                "option": [
                    {"name": "PackChoice", "value": "CurrentPack"},
                ],
            },
            {"name": "ClaimShopDailyReward", "option": []},
            {
                "name": "WonderPick",
                "option": [
                    {"name": "WonderPickStrategy", "value": "FirstPlayer"},
                    {"name": "WonderPickUseHourglass", "value": "No"},
                ],
            },
            {"name": "ClaimDailyMissions", "option": []},
        ],
        "win32": {
            "_placeholder": 0,
        },
        "wlroots": {
            "wlr_socket_path": "",
        },
    }

    maa_option = {
        "draw_quality": 85,
        "logging": True,
        "save_draw": False,
        "save_on_error": True,
        "stdout_level": 2,
    }

    dump_json(config_path / "maa_pi_config.json", maa_pi_config)
    dump_json(config_path / "maa_option.json", maa_option)


def install_docs():
    for file_name in ["README.md", "LICENSE"]:
        shutil.copy2(working_dir / file_name, install_path)


def maa_pi_cli_name():
    return "MaaPiCli.exe" if os_name == "win" else "MaaPiCli"


def verify_install():
    required_paths = [
        "interface.json",
        "README.md",
        "LICENSE",
        "resource",
        "tasks",
        "locales",
        "maafw",
        "MaaPTCGP.exe" if os_name == "win" else "MaaPTCGP",
    ]
    missing = [path for path in required_paths if not (install_path / path).exists()]
    if missing:
        print("Install verification failed. Missing:")
        for path in missing:
            print(f"  {path}")
        sys.exit(1)

    forbidden = []
    forbidden.extend(install_path.rglob(".archives"))
    forbidden.extend(install_path.rglob("*.bak"))
    forbidden.extend(install_path.rglob(".DS_Store"))
    if forbidden:
        print("Install verification failed. Forbidden files/directories found:")
        for path in forbidden[:50]:
            print(f"  {path.relative_to(install_path)}")
        sys.exit(1)

    interface = load_json(install_path / "interface.json")
    resource_names = {item.get("name") for item in interface.get("resource", [])}
    if "Dev" in resource_names and not is_dev_install_version():
        print('Install verification failed. Release interface must not include "Dev" resource.')
        sys.exit(1)

    if not is_dev_install_version():
        for task_file in (install_path / "tasks").rglob("*.json"):
            text = task_file.read_text(encoding="utf-8")
            if '"Dev"' in text:
                print(f'Install verification failed. Release task still references "Dev": {task_file}')
                sys.exit(1)


def verify_cli_install():
    required_paths = [
        "interface.json",
        "resource",
        "tasks",
        "locales",
        "config/maa_pi_config.json",
        "config/maa_option.json",
        maa_pi_cli_name(),
    ]
    missing = [path for path in required_paths if not (install_cli_path / path).exists()]
    if missing:
        print("CLI install verification failed. Missing:")
        for path in missing:
            print(f"  {path}")
        sys.exit(1)


if __name__ == "__main__":
    require_supported_target()
    clean_install()
    clean_install_cli()
    install_mxu_shell()
    install_maafw_for_mxu()
    install_resource()
    install_docs()
    verify_install()
    install_maafw_for_cli()
    install_cli_resource()
    verify_cli_install()

    print(f"Install MXU-only release to {install_path} successfully.")
    print(f"Install MaaPiCli development runtime to {install_cli_path} successfully.")
