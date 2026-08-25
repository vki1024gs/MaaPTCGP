# MXU 多开切换工具

这是一个可选开关工具。没有运行它时，MaaPTCGP 继续使用官方 MXU v2.3.1 的默认全局标签锁。

启用后，一个标签正在运行任务时仍可切换到另一个标签，从而在另一个 ADB 设备上启动任务；任务运行中也可进入中控台视图，同时查看各实例状态和画面。运行期间仍禁止新建、关闭、重命名、右键操作和拖动标签。请勿让两个实例同时控制同一个 ADB 设备。

这是实验性功能。MXU 上游加入全局锁是为了规避并发运行时的界面状态干扰和异常；本工具只放开标签切换和中控台入口，并不改写 MXU 的任务调度器。即使使用不同 ADB，首次也应只运行短任务验证，出现状态串扰、卡住或崩溃时立即停止并恢复官方版本。

## 支持范围

- Windows x86_64 / ARM64
- macOS x86_64 / ARM64
- Linux x86_64
- 仅支持 MXU v2.3.1

## 开关方式

同一个命令反复运行即可切换：

- 当前是官方模式：构建并启用多开模式。
- 当前是多开模式：还原启用前保存的官方 MXU。
- 使用 `--check`：只显示状态并检查下一次切换，不修改文件。

如果已启用旧版多开模式，更新本工具后需要运行两次：第一次校验还原点并恢复官方 MXU，第二次才构建并启用当前版本的多开模式。这个过程不会覆盖或复用旧的非官方程序作为还原点。

启用时会在 MaaPTCGP 旁边建立 `.mxu-multi-instance-state` 还原点目录，并记录原始程序的 SHA-256。还原时会先校验该还原点，成功后删除整个状态目录，不遗留无用的旧程序。

## 本机构建要求

工具不会下载预编译的非官方 MXU。首次启用需要安装 Python 3、Git、Node.js 20+、pnpm、Rust/rustup，以及对应平台的 Tauri 系统构建依赖。关闭多开并还原时只需要 Python，不需要重新构建或联网。

先完全退出 MaaPTCGP，然后在 MaaPTCGP 仓库根目录执行：

```bash
python3 tools/mxu_multi_instance/toggle_mxu_multi_instance.py --check
python3 tools/mxu_multi_instance/toggle_mxu_multi_instance.py
```

Windows 可以将 `python3` 替换为 `py`：

```powershell
py tools\mxu_multi_instance\toggle_mxu_multi_instance.py --check
py tools\mxu_multi_instance\toggle_mxu_multi_instance.py
```

工具固定使用 MXU v2.3.1 对应提交，先校验源码差异与构建结果，再保存官方还原点并原子替换当前可执行文件。失败不会破坏当前程序；成功后自动清理源码、构建目录和替换过程中的临时文件。

工具不会修改 MaaPTCGP 资源、任务、ADB 配置或 MXU 用户配置。自行构建的可执行文件不再具有官方发布文件的签名；macOS 使用临时签名，Windows 构建后的程序图标也可能恢复为 MXU 上游图标。

再次运行本工具即可恢复官方 MXU。必要时仍可通过重新解压同版本 MaaPTCGP 安装包手动恢复。MXU 用户配置位于系统应用数据目录，不会被本工具修改。

MXU 源码采用 GPL-3.0 许可证。工具使用的上游仓库、固定提交和完整源码差异均在 `toggle_mxu_multi_instance.py` 与同目录 `.diff` 文件中公开。
