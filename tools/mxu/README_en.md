# Local MXU tools

[简体中文](README.md) | **English**

Run from the repository root. Launch and restart scripts are macOS-only and target this checkout's `install/MaaPTCGP`, not another installation in Applications.

| Tool | Purpose |
| --- | --- |
| `open-mxu.sh` | Open MXU using the system `open` command |
| `restart-mxu.sh` | Terminate processes whose command line matches that executable path, wait 1 second, then reopen; this interrupts running tasks |

```bash
bash tools/mxu/open-mxu.sh
bash tools/mxu/restart-mxu.sh
```

A working `install/MaaPTCGP` must already exist. For the separate ADB helper and local macOS app rebuilding tool, see the [parent guide](../README_en.md).
