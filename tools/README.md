# Tools

This directory contains project maintenance and release helpers.

- `configure.py`: prepares the default OCR model in `assets/resource/model/ocr/`.
- `install.py`: builds the release runtime layout used by package workflows.
- `check_i18n.py`: checks Project Interface localization references.
- `validate_schema.py`: validates pipeline, interface, and task JSON files.
- `strip_mpe_metadata.py`: removes editor-only pipeline metadata for the public repository.
- `package_macos_dmg.sh`: packages a macOS dmg for release workflows.
- `rebuild_macos_app.sh`: rebuilds a local macOS `.app` for development/testing.

These tools are intended for maintainers. End users should normally download
packages from GitHub Releases instead of running these scripts directly.
