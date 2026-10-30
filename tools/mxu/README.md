# MXU 本地工具

**简体中文** | [English](README_en.md)

从仓库根目录运行。启停脚本仅适用于 macOS，目标是本仓库的 `install/MaaPTCGP`，不是 Applications 中的其他安装。

| 工具 | 用途 |
| --- | --- |
| `open-mxu.sh` | 使用系统 `open` 打开 MXU |
| `restart-mxu.sh` | 终止命令行匹配该程序路径的进程，等待 1 秒后重新打开；会中断正在运行的任务 |

```bash
bash tools/mxu/open-mxu.sh
bash tools/mxu/restart-mxu.sh
```

运行前需有可用的 `install/MaaPTCGP`。独立的 ADB 辅助与 macOS 本地重打包工具见 [上级说明](../README.md)。
