# MXU multi-instance toggle

[简体中文](README.md) | **English**

This optional tool switches between official MXU v2.3.1 behavior and a locally built multi-instance mode. Without running it, MaaPTCGP keeps the official global tab lock.

The modified mode allows switching tabs and opening the dashboard while tasks run, so separate instances can operate separate ADB devices. Creating, closing, renaming, right-clicking, and dragging tabs remain blocked during execution. Never let two instances control the same device.

This is experimental. The upstream lock prevents UI state interference during concurrent runs. This tool changes tab and dashboard access, not task scheduling. Start with short tasks on separate devices; stop and restore the official version if state interference, hangs, or crashes occur.

## Supported targets

- Windows x86_64 / ARM64
- macOS x86_64 / ARM64
- Linux x86_64
- MXU v2.3.1 only

## Usage

Run from the repository root. Fully exit MaaPTCGP before switching modes; `--check` is read-only and can be used while it runs.

```bash
python3 tools/mxu/multi_instance/toggle_mxu_multi_instance.py --check
python3 tools/mxu/multi_instance/toggle_mxu_multi_instance.py
```

On Windows:

```powershell
py tools\mxu\multi_instance\toggle_mxu_multi_instance.py --check
py tools\mxu\multi_instance\toggle_mxu_multi_instance.py
```

Use `--target` to specify the MaaPTCGP executable explicitly. Otherwise it searches the project/package root first, then `install/`. `--yes` skips the interactive confirmation.

Running the tool in official mode builds and enables multi-instance mode. Running it again restores the saved official executable. `--check` reports the current mode and checks prerequisites for the next switch without downloading, building, or replacing files.

For an older enabled version, run twice after updating the tool: first restore the official executable, then build and enable the current modification. It does not reuse a modified executable as the official restore point.

## Requirements and restoration

Enabling requires Python 3, Git, Node.js 20+, pnpm, Rust/rustup, and the platform's Tauri system dependencies. The tool builds from a pinned MXU v2.3.1 source commit rather than downloading unofficial binaries. Restoration only needs Python and does not require Node, Rust, rebuilding, or network access.

The matching `.diff` file must remain beside the script. The tool verifies the source changes and build output, stores the official executable and its SHA-256 in `.mxu-multi-instance-state` beside the target, and replaces the executable atomically. Restoration verifies the backup hash before use and removes the restore state after success. Temporary source and build directories are cleaned up.

The tool does not change MaaPTCGP resources, tasks, ADB settings, or MXU user settings. The locally built executable no longer has the official release signature; macOS uses ad-hoc signing, and the Windows icon may revert to the upstream MXU icon. Re-extracting the same official release is another restoration option. MXU user settings remain in the system application data directory.

MXU source is licensed under GPL-3.0. The upstream repository, pinned commit, and complete source patch are provided in `toggle_mxu_multi_instance.py` and its adjacent `.diff` file.
