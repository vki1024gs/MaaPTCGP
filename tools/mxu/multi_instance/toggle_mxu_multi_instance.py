#!/usr/bin/env python3
"""在官方 MXU 与 MaaPTCGP 多开版 MXU 之间安全切换。

启用时，本工具从固定提交构建 MXU，只应用同目录的源码差异，并在替换前
保存带 SHA-256 校验的官方程序。还原时直接使用该还原点，不需要重新构建
或联网。所有可执行文件替换都在目标目录内原子完成。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


MXU_REPOSITORY = "https://github.com/MistEO/MXU.git"
MXU_COMMIT = "4b0ea0b45a11b2695f410bc7d4a421b525c7c33c"
MXU_VERSION = "2.3.1"
MULTI_INSTANCE_VERSION = "2.3.1+maaptcgp.multi.2"
# 编译进二进制的版本标记，同时用于判断当前运行模式。
BUILD_MARKER = MULTI_INSTANCE_VERSION.encode()
# 保留旧版本标记，确保更新工具后仍能识别、校验并还原已启用的多开版。
LEGACY_BUILD_MARKERS = (b"2.3.1+maaptcgp.multi.1",)
SUPPORTED_BUILD_MARKERS = (BUILD_MARKER, *LEGACY_BUILD_MARKERS)
# 还原点清单格式版本；以后调整清单结构时必须递增。
STATE_VERSION = 1


class ToolError(RuntimeError):
    pass


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> str:
    display = " ".join(command)
    print(f"+ {display}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
    except OSError as exc:
        raise ToolError(f"无法运行命令：{display}（{exc}）") from exc
    if result.returncode != 0:
        output = (result.stdout or "").strip()
        if output:
            print(output)
        raise ToolError(f"命令执行失败（退出码 {result.returncode}）：{display}")
    return (result.stdout or "").strip()


def executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ToolError(f"缺少构建工具：{name}")
    return path


def host_target() -> tuple[str, str]:
    """把当前系统和架构映射为 MXU 官方支持的 Rust target。"""

    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64"}.get(
        machine, machine
    )
    targets = {
        ("darwin", "x86_64"): ("x86_64-apple-darwin", "mxu"),
        ("darwin", "aarch64"): ("aarch64-apple-darwin", "mxu"),
        ("windows", "x86_64"): ("x86_64-pc-windows-msvc", "mxu.exe"),
        ("windows", "aarch64"): ("aarch64-pc-windows-msvc", "mxu.exe"),
        ("linux", "x86_64"): ("x86_64-unknown-linux-gnu", "mxu"),
    }
    try:
        return targets[(system, machine)]
    except KeyError as exc:
        raise ToolError(f"MXU v{MXU_VERSION} 没有支持此系统架构：{system}/{machine}") from exc


def default_target() -> Path:
    """同时支持从源码树和已发布安装包中直接运行。"""

    script_dir = Path(__file__).resolve().parent
    project_or_package_root = script_dir.parent.parent.parent
    name = "MaaPTCGP.exe" if platform.system() == "Windows" else "MaaPTCGP"
    candidates = [
        project_or_package_root / name,
        project_or_package_root / "install" / name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def validate_binary_format(path: Path) -> None:
    """仅接受当前操作系统可执行的 PE、ELF 或 Mach-O 文件。"""

    if not path.is_file():
        raise ToolError(f"找不到 MXU 可执行文件：{path}")
    header = path.read_bytes()[:4]
    system = platform.system()
    valid = (
        (system == "Windows" and header[:2] == b"MZ")
        or (system == "Linux" and header == b"\x7fELF")
        or (
            system == "Darwin"
            and header
            in {
                b"\xfe\xed\xfa\xce",
                b"\xce\xfa\xed\xfe",
                b"\xfe\xed\xfa\xcf",
                b"\xcf\xfa\xed\xfe",
                b"\xca\xfe\xba\xbe",
                b"\xbe\xba\xfe\xca",
            }
        )
    )
    if not valid:
        raise ToolError("目标文件格式与当前操作系统不匹配，拒绝替换。")


def inspect_target(path: Path) -> str:
    """校验目标属于 MXU v2.3.1，并返回 official 或 enabled。"""

    validate_binary_format(path)
    if not (path.parent / "interface.json").is_file():
        raise ToolError(f"目标目录缺少 interface.json，拒绝修改不明可执行文件：{path.parent}")

    binary = path.read_bytes()
    if any(marker in binary for marker in SUPPORTED_BUILD_MARKERS):
        return "enabled"
    if MXU_VERSION.encode() not in binary:
        raise ToolError(f"目标不是可确认的 MXU v{MXU_VERSION}，无法启用此版本的多开功能。")
    return "official"


def sha256(path: Path) -> str:
    """分块计算大文件哈希，避免把第二份二进制完整读入内存。"""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_paths(target: Path) -> tuple[Path, Path, Path]:
    """将还原点放在目标旁边，确保它跟随同一份 MaaPTCGP 安装目录。"""

    state_dir = target.parent / ".mxu-multi-instance-state"
    backup = state_dir / f"{target.name}.official"
    manifest = state_dir / "state.json"
    return state_dir, backup, manifest


def load_restore_point(target: Path) -> tuple[Path, dict[str, object]]:
    """完整验证还原点身份、版本、格式和内容哈希。"""

    state_dir, backup, manifest = restore_paths(target)
    if not backup.is_file() or not manifest.is_file():
        raise ToolError(f"缺少完整还原点，无法安全还原：{state_dir}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"无法读取还原点状态：{manifest}") from exc
    if (
        data.get("state_version") != STATE_VERSION
        or data.get("target_name") != target.name
        or data.get("mxu_version") != MXU_VERSION
        or data.get("mxu_commit") != MXU_COMMIT
    ):
        raise ToolError("还原点信息与当前工具或目标文件不匹配。")
    validate_binary_format(backup)
    backup_binary = backup.read_bytes()
    if (
        any(marker in backup_binary for marker in SUPPORTED_BUILD_MARKERS)
        or MXU_VERSION.encode() not in backup_binary
    ):
        raise ToolError("还原点不是可确认的官方 MXU v2.3.1。")
    if sha256(backup) != data.get("sha256"):
        raise ToolError("还原点哈希校验失败，拒绝还原。")
    return backup, data


def save_restore_point(target: Path) -> None:
    """事务式保存官方程序；已有同源还原点时安全复用。"""

    state_dir, backup, manifest = restore_paths(target)
    original_hash = sha256(target)
    if state_dir.exists():
        existing_backup, data = load_restore_point(target)
        if data.get("sha256") != original_hash or sha256(existing_backup) != original_hash:
            raise ToolError(f"已有还原点与当前官方程序不一致：{state_dir}")
        return

    # 先写临时文件并校验，再逐个原子改名；中途失败会清理本次状态。
    state_dir.mkdir()
    staged_backup = state_dir / f".{backup.name}.new-{os.getpid()}"
    staged_manifest = state_dir / f".{manifest.name}.new-{os.getpid()}"
    try:
        shutil.copy2(target, staged_backup)
        if sha256(staged_backup) != original_hash:
            raise ToolError("原始 MXU 还原点复制校验失败。")
        os.replace(staged_backup, backup)
        state = {
            "state_version": STATE_VERSION,
            "target_name": target.name,
            "mxu_version": MXU_VERSION,
            "mxu_commit": MXU_COMMIT,
            "sha256": original_hash,
        }
        staged_manifest.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staged_manifest, manifest)
        load_restore_point(target)
    except Exception:
        for path in (staged_backup, staged_manifest, backup, manifest):
            if path.exists():
                path.unlink()
        if state_dir.exists():
            state_dir.rmdir()
        raise


def remove_restore_point(target: Path) -> None:
    """还原成功后只删除本工具拥有的文件，不清理未知内容。"""

    state_dir, backup, manifest = restore_paths(target)
    for path in (backup, manifest):
        if path.exists():
            path.unlink()
    if state_dir.exists():
        try:
            state_dir.rmdir()
        except OSError as exc:
            raise ToolError(f"官方程序已还原，但状态目录含有未知文件，请检查：{state_dir}") from exc


def ensure_not_running(target: Path) -> None:
    """禁止替换正在运行的程序，尤其避免 Windows 文件占用失败。"""

    name = target.name.lower()
    if platform.system() == "Windows":
        tasklist = executable("tasklist")
        output = run([tasklist, "/FI", f"IMAGENAME eq {target.name}"], capture=True).lower()
        if name in output:
            raise ToolError(f"请先完全退出 {target.name}，再运行多开切换工具。")
        return

    ps = executable("ps")
    output = run([ps, "-axo", "pid=,comm="], capture=True)
    for line in output.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) == 2 and Path(fields[1]).name.lower() == name:
            raise ToolError(f"请先完全退出 {target.name}，再运行多开切换工具。")


def check_toolchain(rust_target: str) -> dict[str, str]:
    """启用前一次性检查全部构建工具，不在脚本内静默安装依赖。"""

    tools = {
        "git": executable("git"),
        "node": executable("node"),
        "pnpm": executable("pnpm"),
        "cargo": executable("cargo"),
        "rustup": executable("rustup"),
    }
    node_version = run([tools["node"], "--version"], capture=True).lstrip("v")
    try:
        node_major = int(node_version.split(".", 1)[0])
    except ValueError as exc:
        raise ToolError(f"无法识别 Node.js 版本：{node_version}") from exc
    if node_major < 20:
        raise ToolError(f"需要 Node.js 20 或更高版本，当前为 {node_version}")

    installed = run([tools["rustup"], "target", "list", "--installed"], capture=True).splitlines()
    if rust_target not in installed:
        raise ToolError(
            f"Rust 尚未安装目标 {rust_target}。请先运行：rustup target add {rust_target}"
        )
    return tools


def update_json_version(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = MULTI_INSTANCE_VERSION
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_cargo_version(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version = "[^"]+"$',
        f'version = "{MULTI_INSTANCE_VERSION}"',
        text,
        count=1,
    )
    if count != 1:
        raise ToolError("无法更新 MXU Cargo.toml 版本，源码结构可能已经变化。")
    path.write_text(updated, encoding="utf-8")


def clone_and_apply_change(source: Path, source_diff: Path, tools: dict[str, str]) -> None:
    """浅拉取固定提交，并在构建前验证源码差异能够精确应用。"""

    run([tools["git"], "init", str(source)])
    run([tools["git"], "-C", str(source), "remote", "add", "origin", MXU_REPOSITORY])
    run(
        [
            tools["git"],
            "-C",
            str(source),
            "fetch",
            "--depth=1",
            "origin",
            MXU_COMMIT,
        ]
    )
    run([tools["git"], "-C", str(source), "checkout", "--detach", "FETCH_HEAD"])
    actual = run([tools["git"], "-C", str(source), "rev-parse", "HEAD"], capture=True)
    if actual != MXU_COMMIT:
        raise ToolError(f"MXU 源码提交校验失败：{actual}")
    # 差异文件使用零上下文以避免补丁文本自身产生尾随空格；固定提交校验
    # 保证它不会被误用到结构相似但版本不同的源码。
    run(
        [
            tools["git"],
            "-C",
            str(source),
            "apply",
            "--unidiff-zero",
            "--check",
            str(source_diff),
        ]
    )
    run(
        [tools["git"], "-C", str(source), "apply", "--unidiff-zero", str(source_diff)]
    )


def build(source: Path, rust_target: str, binary_name: str, tools: dict[str, str]) -> Path:
    """使用上游锁文件构建，并拒绝没有多开版本标记的产物。"""

    update_json_version(source / "package.json")
    update_json_version(source / "src-tauri" / "tauri.conf.json")
    update_cargo_version(source / "src-tauri" / "Cargo.toml")
    run([tools["pnpm"], "install", "--frozen-lockfile"], cwd=source)
    run(
        [tools["pnpm"], "tauri", "build", "--no-bundle", "--target", rust_target],
        cwd=source,
    )
    result = source / "src-tauri" / "target" / rust_target / "release" / binary_name
    if not result.is_file() or result.stat().st_size == 0:
        raise ToolError(f"构建完成但找不到 MXU 可执行文件：{result}")
    if BUILD_MARKER not in result.read_bytes():
        raise ToolError("构建结果缺少多开版本标记，拒绝安装。")
    return result


def install_atomically(source: Path, target: Path, *, sign_macos: bool) -> None:
    """在目标文件系统内暂存、验证签名并原子替换可执行文件。"""

    staged = target.with_name(f".{target.name}.multi-new-{os.getpid()}")
    try:
        shutil.copy2(source, staged)
        if platform.system() != "Windows" and sign_macos:
            staged.chmod(target.stat().st_mode)
        if platform.system() == "Darwin" and sign_macos:
            codesign = executable("codesign")
            run([codesign, "--force", "--sign", "-", str(staged)])
            run([codesign, "--verify", "--strict", str(staged)])
        os.replace(staged, target)
    finally:
        if staged.exists():
            staged.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="在 MXU v2.3.1 官方模式和多实例运行模式之间切换。"
    )
    parser.add_argument("--target", type=Path, help="MaaPTCGP/MaaPTCGP.exe 的路径")
    parser.add_argument("--check", action="store_true", help="仅显示当前状态并检查下一次切换")
    parser.add_argument("--yes", action="store_true", help="跳过切换前的交互确认")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = (args.target or default_target()).expanduser().resolve()
    source_diff = Path(__file__).resolve().with_name("mxu-v2.3.1-multi-instance.diff")
    try:
        rust_target, binary_name = host_target()
        current_state = inspect_target(target)
        # 状态查询只读，可在 MXU 运行时执行；真正替换前必须完全退出。
        if not args.check:
            ensure_not_running(target)
        print(f"目标：{target}")
        print(f"平台：{rust_target}")
        if current_state == "enabled":
            # 关闭路径只依赖本地还原点，不检查 Node/Rust，也不访问网络。
            backup, data = load_restore_point(target)
            print("当前状态：多开模式（再次运行将还原官方模式）")
            print(f"官方还原点：{backup} [{str(data['sha256'])[:12]}]")
            if args.check:
                print("还原检查通过；还原不需要 Node、Rust 或网络。")
                return 0
            if not args.yes:
                answer = input("确认关闭多开并还原官方 MXU？[y/N] ").strip().lower()
                if answer not in {"y", "yes"}:
                    print("已取消，没有修改任何文件。")
                    return 0
            install_atomically(backup, target, sign_macos=False)
            if sha256(target) != data["sha256"]:
                raise ToolError("官方 MXU 已写入，但写入后的哈希校验失败。")
            remove_restore_point(target)
            print("MXU 已还原为官方模式，还原点和状态文件已清理。")
            return 0

        # 启用路径在碰触官方程序之前完成环境检查、源码构建和产物验证。
        if not source_diff.is_file():
            raise ToolError(f"多开源码差异文件缺失：{source_diff}")
        tools = check_toolchain(rust_target)
        print("当前状态：官方模式（再次运行将启用多开）")
        print(f"源码：MXU v{MXU_VERSION} ({MXU_COMMIT})")
        if args.check:
            print("启用检查通过；尚未下载、构建或替换任何文件。")
            return 0
        if not args.yes:
            answer = input("确认构建并启用 MXU 多开？[y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("已取消，没有修改任何文件。")
                return 0

        with tempfile.TemporaryDirectory(prefix="maaptcgp-mxu-multi-") as temp:
            source = Path(temp) / "MXU"
            clone_and_apply_change(source, source_diff, tools)
            built = build(source, rust_target, binary_name, tools)
            save_restore_point(target)
            try:
                install_atomically(built, target, sign_macos=True)
            except Exception:
                # 原子替换失败时目标仍是官方程序，还原点也不应成为残留。
                remove_restore_point(target)
                raise
        print("MXU 多开功能已启用；原始官方程序已安全保存，可再次运行本工具还原。")
        return 0
    except ToolError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        print("切换未完成；请根据上方信息检查当前模式和还原点。", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"错误：文件操作失败（{exc}）", file=sys.stderr)
        print("切换使用原子替换，请检查当前模式和还原点状态。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
