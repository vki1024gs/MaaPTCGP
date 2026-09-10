# 工具说明

**简体中文** | [English](README_en.md)

以下命令均从仓库根目录运行。Python 工具使用 Python 3。

| 目录 | 用途 |
| --- | --- |
| [ci/](ci/) | CI 校验、发布打包及安装包依赖 |
| [checks/](checks/) | 开发者提交前检查与 public 净化 |
| [mxu/](mxu/README.md) | MXU 启停和多开工具 |

## 根目录脚本

### adb_autoconnect.py

本地 ADB 连接辅助工具。默认寻找 macOS BlueStacks 的 `hd-adb`，检查一组预设的本机端口；也可通过 `--adb` 指定 ADB，通过 `--ports` 指定端口。已在线设备会跳过连接，其他监听端口会尝试 `adb connect`，随后查询设备状态。

```bash
python3 tools/adb_autoconnect.py --ports 5555
python3 tools/adb_autoconnect.py --help
```

示例端口需替换为模拟器实际端口。默认运行一轮；`--watch` 持续重试，`--interval` 设置间隔（默认 5 秒）。它会改变 ADB 连接状态；退出码为 0 不代表所有端口都连接成功，请检查输出。它与安装包中的 macOS ADB 预处理脚本不同，后者由已确认的模拟器进程发现端点。

### rebuild_macos_app.sh

仅用于 macOS 本地开发测试，将已有 `install/` 封装为 `.app`，不编译 MXU。生成图标、版本信息并临时签名，移除隔离标记；完成后默认打开 Finder 并建立 Applications 快捷方式。

```bash
bash tools/rebuild_macos_app.sh install build/MaaPTCGP.app v0.2.4
```

输出 `.app` 已存在时会被替换。低于 1.0 的版本要求输入接口中有 `Dev` 资源，并将它改为本仓库的绝对资源路径；第六个参数可指定其他资源目录。此类应用仅供本地使用。1.0 及以上不注入该路径。可设置 `MXU_OPEN_INSTALL_WINDOW=0` 关闭自动打开 Finder；临时签名不等于 Apple 公证。

### setup_ocr_model.py

原名 `configure.py`。将 `assets/MaaCommonAssets/OCR/ppocr_v5/zh_cn` 复制到 `assets/resource/model/ocr`，初始化本地 OCR 模型。

```bash
python3 tools/setup_ocr_model.py
```

需要先准备好 MaaCommonAssets 源文件。目标目录已存在时完全跳过，不覆盖、不更新，也不检查已有模型是否完整。当前 CI 不调用此工具，打包由 `ci/install.py` 自行处理 OCR 模型。

## CI 工具

`ci/` 集中 GitHub Actions 直接使用的工具及打包依赖。命令从仓库根目录运行。

| 文件 | 用途 |
| --- | --- |
| `install.py` | 组装并校验 `install/` 与 `install-cli/`，复制程序、资源、任务、翻译及 OCR 模型 |
| `requirements.txt` | Python 打包与 Schema 校验依赖 |
| `validate_schema.py` | 校验资源、接口与任务 JSON/JSONC 的 Schema；开发者也可手动调用 |
| `package_macos_dmg.sh` | 在 macOS 上将安装目录封装为临时签名的 `.app` 和 DMG；需要 `create-dmg` |
| `maa_adb_autoconnect_macos.sh` | 被打包为 macOS 的 `bin/maa-adb-autoconnect`，用户启用对应选项后由 MXU 执行 |

```bash
python3 -m pip install -r tools/ci/requirements.txt
python3 tools/ci/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --interface-files assets/interface.json --task-dirs assets/tasks
```

发布打包示例（需事先准备仓库根目录的 `MXU/`、`deps/` 和资源）：

```bash
python3 tools/ci/install.py v0.2.4 macos aarch64
bash tools/ci/package_macos_dmg.sh install build/MaaPTCGP.dmg v0.2.4
```

`install.py` 会删除并重建现有 `install/` 和 `install-cli/`，不要用于日常开发资源同步。支持 Windows/macOS 的 x86_64、aarch64，以及 Linux x86_64。DMG 工具会替换同名输出文件；临时签名不等于公证。

ADB 脚本不在 CI 中执行连接操作，只作为安装包依赖。运行时从已确认的 BlueStacks 或 MuMuPlayer Pro 进程发现端点，必要时连接或修复 ADB 服务，不使用固定模拟器端口。

## 提交前检查

从仓库根目录运行。依赖见 本页 CI 工具说明。

```bash
python3 tools/checks/check_i18n.py
python3 tools/ci/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --interface-files assets/interface.json --task-dirs assets/tasks
npx @nekosu/maa-tools check
```

`check_i18n.py` 检查接口和任务中的翻译引用、各语言缺失项及引用文件；也可使用 `npm run check:i18n`。Schema 检查只证明格式兼容，不证明实际任务运行成功。`maa-tools` 需要 Node.js、项目依赖及可用的 MaaFramework 运行依赖。

### 仅用于 public 的净化检查

以下命令必须在 public 仓库根目录运行：

```bash
python3 tools/checks/strip_mpe_metadata.py
```

默认只检查，不写入；发现编辑器字段或 `desc` 时返回非零。确认需要净化 public 后再添加 `--write`。该工具会拒绝在含开发标记的 dev 仓库运行，不要对 dev 执行净化。可用 `--root` 显式指定目标仓库。
