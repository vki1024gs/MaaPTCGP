# Tools

[简体中文](README.md) | **English**

Run all commands below from the repository root. Python tools require Python 3.

| Directory | Purpose |
| --- | --- |
| [ci/](ci/) | CI validation, release packaging, and package dependencies |
| [checks/](checks/) | Developer checks before pushing and public sanitization |
| [mxu/](mxu/README_en.md) | MXU launch, restart, and multi-instance tools |

## Scripts in this directory

### adb_autoconnect.py

A local ADB connection helper. By default, it looks for macOS BlueStacks `hd-adb` and checks a preset list of local ports. Use `--adb` to specify ADB and `--ports` to specify ports. It skips connecting devices already online, tries `adb connect` for other listening ports, then queries their state.

```bash
python3 tools/adb_autoconnect.py --ports 5555
python3 tools/adb_autoconnect.py --help
```

Replace the example port with your emulator's actual port. It runs once by default; `--watch` repeats checks, and `--interval` sets the delay (5 seconds by default). It changes ADB connection state. Exit code 0 does not mean every connection succeeded; check the output. Unlike this helper, the packaged macOS ADB pretask discovers endpoints from verified emulator processes.

### rebuild_macos_app.sh

For local development and testing on macOS only. Wraps an existing `install/` directory in an `.app` without compiling MXU. It adds an icon and version metadata, applies ad-hoc signing, removes quarantine attributes, and opens Finder with an Applications shortcut by default.

```bash
bash tools/rebuild_macos_app.sh install build/MaaPTCGP.app v0.2.5
```

An existing output `.app` is replaced. Versions below 1.0 require a `Dev` resource in the input interface and rewrite it to this checkout's absolute resource path; the sixth argument can specify another resource directory. Such apps are for local use only. Versions 1.0 and above do not receive this path. Set `MXU_OPEN_INSTALL_WINDOW=0` to disable opening Finder. Ad-hoc signing is not Apple notarization.

### setup_ocr_model.py

Previously named `configure.py`. Initializes local OCR models by copying `assets/MaaCommonAssets/OCR/ppocr_v5/zh_cn` to `assets/resource/model/ocr`.

```bash
python3 tools/setup_ocr_model.py
```

The MaaCommonAssets source files must already be available. If the destination directory exists, it skips copying entirely: it does not overwrite, update, or check existing models for completeness. CI does not call this tool; `ci/install.py` handles OCR models during packaging.

## CI tools

`ci/` contains tools called directly by GitHub Actions and dependencies included during packaging. Run commands from the repository root.

| File | Purpose |
| --- | --- |
| `install.py` | Assemble and validate `install/` and `install-cli/`, copying executables, resources, tasks, translations, and OCR models |
| `requirements.txt` | Python dependencies for packaging and Schema validation |
| `validate_schema.py` | Validate resource, interface, and task JSON/JSONC against schemas; also available for manual developer checks |
| `package_macos_dmg.sh` | Wrap an install directory in an ad-hoc signed `.app` and DMG on macOS; requires `create-dmg` |
| `maa_adb_autoconnect_macos.sh` | Packaged as macOS `bin/maa-adb-autoconnect`; MXU runs it when the user enables the corresponding option |

```bash
python3 -m pip install -r tools/ci/requirements.txt
python3 tools/ci/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --interface-files assets/interface.json --task-dirs assets/tasks
```

Release packaging example (prepare `MXU/`, `deps/`, and resources at the repository root first):

```bash
python3 tools/ci/install.py v0.2.5 macos aarch64
bash tools/ci/package_macos_dmg.sh install build/MaaPTCGP.dmg v0.2.5
```

`install.py` deletes and recreates existing `install/` and `install-cli/` directories. Do not use it for routine development resource syncing. Supported targets are Windows/macOS x86_64 and aarch64, and Linux x86_64. The DMG tool replaces an existing output file. Ad-hoc signing is not notarization.

CI packages the ADB script without running its connection operations. At runtime it discovers endpoints from verified BlueStacks or MuMuPlayer Pro processes and connects or repairs the ADB service when needed, without fixed emulator ports.

## Checks before pushing

Run from the repository root. See the CI tools section on this page for dependencies.

```bash
python3 tools/checks/check_i18n.py
python3 tools/ci/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --interface-files assets/interface.json --task-dirs assets/tasks
npx @nekosu/maa-tools check
```

`check_i18n.py` checks translation references in the interface and tasks, missing entries across languages, and referenced files. It is also available as `npm run check:i18n`. Schema validation proves format compatibility, not successful task execution. `maa-tools` requires Node.js, project dependencies, and available MaaFramework runtime dependencies.

### Public-only sanitization check

Run this command from the public repository root:

```bash
python3 tools/checks/strip_mpe_metadata.py
```

The default mode checks without writing and returns nonzero if editor fields or `desc` are found. Add `--write` only when you intend to sanitize public. The tool refuses to run in a dev repository containing development markers; do not sanitize dev. Use `--root` to specify the target repository explicitly.
