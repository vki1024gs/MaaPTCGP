# MaaPTCGP

MaaPTCGP is a daily automation helper for Pokemon Trading Card Game Pocket.

⚠️ Internal testing stage - adapted for the Chinese game UI. Features are still incomplete and under active development.

## Requirements

- MXU is the recommended client.
- An Android emulator or Android device must be connected through ADB.
- Recognition currently works best with the Chinese game UI.
- Keep the default resource for normal runs. The default resource loads the bundled `resource` directory from the release package.
- This project is still in active development and debugging. Switch to the Dev resource only when developing from source and loading `assets/resource` directly.

## Language Support

MaaPTCGP's MXU interface supports multiple languages, including Chinese and English. Recognition currently works best with the Chinese game UI.

If you use English, Japanese, or another in-game language, recognition may fail or tasks may get stuck. If an error happens, switch the game to Chinese first and try again.

Game updates may change the UI layout and temporarily affect recognition. If a task fails after an update, stop that task and report it with logs and screenshots.

## Main Features

- 🚀Start Game
- 📬Gift Box Mail
- 🎴Open Pack
- 🎟️Daily Shop Ticket
- 🔮Wonder Pick
- ⚔️Event / Random / Step-Up Battle
- 🎁Share Cards
- 📋Daily Missions
- 🛠️Task-Bar Auto Claim
- 👆Swipe Up

## Feedback

If a task gets stuck or recognition fails, please report it through GitHub Issues. Include the task name, device or emulator, game language, and MXU debug logs if possible.
