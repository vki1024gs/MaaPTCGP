<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img alt="MaaPTCGP Logo" src="assets/locales/MaaPTCGP-Tiny.png" width="160" height="160" />
</p>

<div align="center">

# MaaPTCGP

Automation helper for PTCG Pocket, based on MaaFramework. Image recognition + simulated controls, so your hands can rest.  
Powered by [MaaFramework](https://github.com/MaaXYZ/MaaFramework)

[简体中文](README.md) | **English**

</div>

> ⚠️ Internal testing stage - features are incomplete and still under active development.

## Main Features

### 🚀 Launch

- 🚀 Launch the game and converge to a stable home screen

### 📆 Daily

- 📬 Claim gift box mail rewards
- 🎴 Open available daily packs with pack selection options
- 🎟️ Claim the daily free shop ticket
- 🔮 Run Wonder Pick reward flow
- ⚔️ Run event, random, and step-up battle flows
- 🎁 Share selected-rarity cards with starred friends
- 📋 Claim daily mission rewards

### 🛠️ Utility

- 👆 Provide helper actions such as swipe-up sending
- 📌 Provide auto-claim for task-bar red dots (in development and may be unstable)
- 🛠️ Provide development resources for local pipeline validation

## Requirements

- [MXU](https://github.com/MistEO/MXU) is the recommended graphical client
- Android emulator or Android device connected through MaaFramework ADB controller
- Game display short side configured around 720 px
- Current recognition resources are primarily developed against Chinese game UI

## Language Support

MaaPTCGP's MXU interface supports multiple languages, including Chinese and English, but the automation scripts are currently developed and tested mainly against the Chinese game UI.

If you use English, Japanese, or another in-game language, recognition errors, stuck flows, or task failures may occur. If an error happens, switch the game to Chinese first and try again. If the issue still happens after switching, please report it.

Game updates may change the UI layout and temporarily affect recognition. If a task fails after an update, stop that task and report it with logs and screenshots.

## Quick Start

1. Download the package for your system from GitHub Releases. On macOS, use tar.gz or dmg.
2. Open MaaPTCGP with MXU.
3. Select an available ADB device in connection settings and confirm screenshots work.
4. Use the default resource for normal runs.
5. Select the tasks you need, or run `Basic Daily Tasks`.
6. For first-time use, run a small number of tasks first and confirm emulator resolution, game language, and recognition stability before combining more tasks.

Battle, Share, and other in-development tasks in `Basic Daily Tasks` are disabled by default. Enable them manually only after testing them separately. Battle mode currently supports event battles, random battles, and step-up battles; random and step-up battles do not use event battle point recovery.

For pipeline development, select the `Dev` resource in MXU to load `assets/resource` directly from source.

The macOS build is not Apple-notarized yet. Whether you download tar.gz or dmg, macOS may say it cannot check the app for malware on first launch. If you trust the GitHub Release source, go to `System Settings -> Privacy & Security` and choose `Open Anyway` within one hour, or run `xattr -dr com.apple.quarantine <MaaPTCGP directory>` on the extracted directory before opening it again.

## Planned Features And Direction

- Expand Wonder Pick and card-sharing strategies
- Continue improving battle and other automation flows
- Track game UI updates and improve daily-task stability and recovery

## Feedback

Please report issues through [GitHub Issues](https://github.com/vki1024gs/MaaPTCGP/issues).

When reporting pipeline failures, include:

- Task name
- Device or emulator
- Game language
- MXU debug logs
- Screenshots when useful

## Development

For more documentation, see the [MaaFramework](https://github.com/MaaXYZ/MaaFramework) repository.

## Acknowledgements

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework)
- [MXU](https://github.com/MistEO/MXU)
- [MPE / MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor)
