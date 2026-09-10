<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img alt="MaaPTCGP Logo" src="assets/locales/MaaPTCGP-Tiny.png" width="256" height="256" />
</p>

<div align="center">

# MaaPTCGP

基于 MaaFramework 的 PTCG Pocket 自动化助手。图像技术 + 模拟控制，解放双手！  
由 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 强力驱动！

**简体中文** | [English](README_en.md)

</div>

> ⚠️ 内测阶段 - 功能尚不完善，正在持续开发中！

## 主要功能

### 🚀 启动

- 🚀 启动游戏并返回首页

### 📆 日常

- 📬 领取礼物盒邮件奖励
- 🎴 拆开可用的每日卡包，支持收藏卡包选择
- 🎟️ 领取每日免费商店票
- 🔮 执行得卡挑战流程
- ⚔️ 执行活动对战、随机对战和分级对战流程，活动对战支持体力恢复设置
- 🎁 分送指定稀有度卡片给星标好友
- 📋 领取日常任务奖励

### 🛠️ 工具

- 👆 提供上滑发送等辅助操作
- 📌 提供任务栏自动领取小工具（开发中，可能不稳定）

## 使用前提

- 推荐使用 [MXU](https://github.com/MistEO/MXU) 作为图形界面客户端
- 通过 MaaFramework ADB 控制器连接安卓模拟器或安卓设备
- 游戏画面短边建议配置为 720 px
- 当前识别资源主要围绕中文游戏界面开发

## 语言适配说明

MaaPTCGP 的 MXU 界面支持中文、英文等多种语言，但脚本功能目前主要基于中文游戏界面开发和测试。

如果使用英文、日文或其他语言的游戏界面，可能会遇到识别错误、流程卡住或功能异常。遇到报错时，请先将游戏切换到中文界面后再尝试；如果切换后问题仍然存在，欢迎提交反馈。

游戏更新可能改变界面布局并暂时影响识别。如果更新后出现异常，请停止相关任务并附上日志和截图反馈。

## 快速开始

1. 从 GitHub Release 下载与你的系统匹配的安装包。macOS 可下载 tar.gz 或 dmg。
2. 使用 MXU 打开 MaaPTCGP。
3. 在连接设置中选择可用的 ADB 设备，并确认截图画面正常。
4. 普通使用选择默认资源。
5. 按需勾选要执行的任务，或直接运行 `基础日常任务`。
6. 首次使用建议先单独运行少量任务，确认模拟器分辨率、游戏语言和识别稳定性后再组合执行。

`基础日常任务` 中的对战、分送等开发中任务默认不勾选，需要时请手动开启并先单独测试。对战任务目前可选择活动对战、随机对战或分级对战；活动对战可按设置处理体力恢复，随机对战和分级对战不使用活动体力恢复。

macOS 版目前未进行 Apple 公证。无论下载 tar.gz 还是 dmg，首次打开时都可能提示无法检查恶意软件；如果你确认来源为本项目 GitHub Release，可前往 `系统设置 -> 隐私与安全性`，在一小时内选择 `仍要打开`，也可对解压后的目录执行 `xattr -dr com.apple.quarantine <MaaPTCGP目录>` 后再打开。

## 计划中的功能与方向

- 扩展得卡挑战和分送卡片的可选策略
- 继续完善对战及其他自动化流程
- 跟进游戏界面更新，提升日常任务稳定性和异常恢复能力

## 问题反馈

请通过 [GitHub Issues](https://github.com/vki1024gs/MaaPTCGP/issues) 反馈问题。

反馈任务卡住或识别失败时，请尽量附上：

- 任务名
- 设备或模拟器
- 游戏语言
- MXU 调试日志
- 必要截图

## 开发说明

更多文档请前往 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 主仓库查看。

## 鸣谢

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework)
- [MXU](https://github.com/MistEO/MXU)
- [MPE / MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor)
