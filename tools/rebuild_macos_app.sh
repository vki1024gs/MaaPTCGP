#!/usr/bin/env bash
set -euo pipefail

# Local development usage:
#   tools/rebuild_macos_app.sh install "$HOME/Applications/MaaPTCGP.app" v0.1.9
#   tools/rebuild_macos_app.sh install "$HOME/Applications/MaaPTCGP.app" v0.1.9 MaaPTCGP io.github.vki1024gs.maaptcgp /path/to/assets/resource
#
# For versions below 1.0, this development wrapper points the copied interface's
# Dev resource at the source tree. An explicitly supplied sixth argument takes
# priority; otherwise assets/resource in this checkout is used. MXU 2.8 always
# prefixes resource paths with the app directory, so the tool encodes the
# absolute source location as a root-anchored relative path with enough parent
# segments to remain valid after the finished app is moved.
# Public DMGs are built by tools/ci/package_macos_dmg.sh instead.
#
# After a successful build, the output directory is opened in Finder with an
# Applications shortcut beside the app, so the app can be installed by dragging
# it onto Applications. Set MXU_OPEN_INSTALL_WINDOW=0 for CI or scripted builds.

if [[ $# -lt 3 ]]; then
  echo "Usage: tools/rebuild_macos_app.sh <install_dir> <output_app> <version> [app_name] [bundle_id] [dev_resource_path]" >&2
  echo "Example: tools/rebuild_macos_app.sh install build/MaaPTCGP.app v0.1.9" >&2
  echo "Custom Dev path: tools/rebuild_macos_app.sh install build/MaaPTCGP.app v0.1.9 MaaPTCGP io.github.vki1024gs.maaptcgp /path/to/assets/resource" >&2
  exit 1
fi

INSTALL_DIR="$1"
OUTPUT_APP="$2"
FULL_VERSION="$3"
APP_NAME="${4:-MaaPTCGP}"
BUNDLE_ID="${5:-io.github.vki1024gs.maaptcgp}"
CUSTOM_DEV_RESOURCE_PATH="${6:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ICON_SOURCE="$PROJECT_ROOT/assets/logo.png"

if [[ ! -d "$INSTALL_DIR" ]]; then
  echo "Missing install directory: $INSTALL_DIR" >&2
  exit 1
fi

INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"

if [[ ! -f "$INSTALL_DIR/$APP_NAME" ]]; then
  echo "Missing macOS executable: $INSTALL_DIR/$APP_NAME" >&2
  exit 1
fi

if [[ "$OUTPUT_APP" != *.app ]]; then
  echo "Output path must end with .app: $OUTPUT_APP" >&2
  exit 1
fi

OUTPUT_PARENT="$(dirname "$OUTPUT_APP")"
OUTPUT_NAME="$(basename "$OUTPUT_APP")"
mkdir -p "$OUTPUT_PARENT"
OUTPUT_PARENT="$(cd "$OUTPUT_PARENT" && pwd)"
OUTPUT_APP="$OUTPUT_PARENT/$OUTPUT_NAME"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

APP_BUNDLE="$WORK_DIR/$OUTPUT_NAME"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
ICON_PLIST_ENTRY=""

if [[ -f "$ICON_SOURCE" ]]; then
  if sips -s format icns "$ICON_SOURCE" \
    --out "$APP_BUNDLE/Contents/Resources/app.icns" >/dev/null 2>&1; then
    ICON_PLIST_ENTRY=$'    <key>CFBundleIconFile</key>\n    <string>app.icns</string>'
  else
    echo "Warning: failed to build app icon; continuing without CFBundleIconFile." >&2
    rm -f "$APP_BUNDLE/Contents/Resources/app.icns"
  fi
fi

# Use ditto without extended attributes/resource forks so downloaded quarantine
# metadata from source files is not carried into the locally rebuilt app.
ditto --noextattr --norsrc "$INSTALL_DIR" "$APP_BUNDLE/Contents/MacOS"

# Do not embed legacy local restore state. codesign treats its backup executable
# as a nested component, and distributing it would duplicate an
# installation-specific restore point.
rm -rf "$APP_BUNDLE/Contents/MacOS/.mxu-multi-instance-state"

SHORT_VERSION="$(echo "$FULL_VERSION" | sed -E 's/^v//' | sed -E 's/-.*//')"
VERSION_MAJOR="${SHORT_VERSION%%.*}"

if [[ "$VERSION_MAJOR" =~ ^[0-9]+$ ]] && (( VERSION_MAJOR < 1 )); then
  APP_INTERFACE="$APP_BUNDLE/Contents/MacOS/interface.json"
  DEV_RESOURCE_PATH="${CUSTOM_DEV_RESOURCE_PATH:-$PROJECT_ROOT/assets/resource}"

  if [[ ! -f "$APP_INTERFACE" ]]; then
    echo "Missing app interface for Dev path injection: $APP_INTERFACE" >&2
    exit 1
  fi
  if [[ ! -d "$DEV_RESOURCE_PATH" ]]; then
    echo "Missing source Dev resource directory: $DEV_RESOURCE_PATH" >&2
    exit 1
  fi

  DEV_RESOURCE_PATH="$(cd "$DEV_RESOURCE_PATH" && pwd -P)"

  python3 - "$APP_INTERFACE" "$DEV_RESOURCE_PATH" <<'PY'
import json
import sys
from pathlib import Path

interface_path = Path(sys.argv[1])
dev_resource_path = Path(sys.argv[2]).resolve()
if not dev_resource_path.is_absolute():
    raise SystemExit(f"Dev resource path is not absolute: {dev_resource_path}")

# MXU 2.8 concatenates every resource path with the directory containing
# interface.json, including strings that begin with '/'. Climb beyond any
# realistic app nesting depth; extra '..' components at the POSIX root are
# harmless, then append the absolute target without its leading slash.
root_relative = dev_resource_path.relative_to(dev_resource_path.anchor)
portable_path = Path(*([".."] * 64), root_relative).as_posix()
interface = json.loads(interface_path.read_text(encoding="utf-8"))

for resource in interface.get("resource", []):
    if resource.get("name") == "Dev":
        resource["path"] = [portable_path]
        interface_path.write_text(
            json.dumps(interface, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )
        print(f"Configured movable Dev resource: {portable_path} -> {dev_resource_path}")
        break
else:
    raise SystemExit('Dev resource was not found in the generated app interface.json')
PY
fi

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
$ICON_PLIST_ENTRY
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$SHORT_VERSION</string>
    <key>CFBundleVersion</key>
    <string>$FULL_VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
</dict>
</plist>
EOF

chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
if [[ -d "$APP_BUNDLE/Contents/MacOS/maafw" ]]; then
  find "$APP_BUNDLE/Contents/MacOS/maafw" -type f -name "Maa*" ! -name "*.dylib" -exec chmod +x {} \;
fi

xattr -dr com.apple.quarantine "$APP_BUNDLE" 2>/dev/null || true
codesign --force --deep --sign - "$APP_BUNDLE"

rm -rf "$OUTPUT_APP"
mv "$APP_BUNDLE" "$OUTPUT_APP"

echo "Rebuilt app: $OUTPUT_APP"
if xattr -p com.apple.quarantine "$OUTPUT_APP" >/dev/null 2>&1; then
  echo "quarantine: present"
else
  echo "quarantine: absent"
fi

codesign --verify --deep --strict "$OUTPUT_APP"
if [[ "$VERSION_MAJOR" =~ ^[0-9]+$ ]] && (( VERSION_MAJOR < 1 )); then
  python3 - "$OUTPUT_APP/Contents/MacOS/interface.json" "$DEV_RESOURCE_PATH" <<'PY'
import json
import sys
from pathlib import Path

interface_path = Path(sys.argv[1])
expected = Path(sys.argv[2]).resolve()
interface = json.loads(interface_path.read_text(encoding="utf-8"))
dev = next((item for item in interface.get("resource", []) if item.get("name") == "Dev"), None)
if not dev or len(dev.get("path", [])) != 1:
    raise SystemExit("Missing single Dev resource path in packaged interface")
actual = (interface_path.parent / dev["path"][0]).resolve()
if actual != expected or not actual.is_dir():
    raise SystemExit(f"Packaged Dev resource path is invalid: {actual}")
print(f"Verified packaged Dev resource path: {actual}")
PY
fi
codesign -dv "$OUTPUT_APP" 2>&1 | sed -n '/Authority=/p;/Signature=/p'

if command -v stapler >/dev/null 2>&1; then
  if stapler validate "$OUTPUT_APP" >/dev/null 2>&1; then
    echo "notarization: stapled ticket present"
  else
    echo "notarization: no stapled ticket"
  fi
else
  echo "notarization: stapler not available"
fi

echo "Note: this app is rebuilt for local development/testing with ad-hoc signing."
echo "Note: this does not provide Developer ID signing or Apple notarization."

if [[ "${MXU_CREATE_APPLICATIONS_LINK:-1}" != "0" ]]; then
  APPLICATIONS_LINK="$OUTPUT_PARENT/Applications"
  if [[ -L "$APPLICATIONS_LINK" ]]; then
    ln -sfn /Applications "$APPLICATIONS_LINK"
  elif [[ -e "$APPLICATIONS_LINK" ]]; then
    echo "Warning: $APPLICATIONS_LINK already exists and is not a symlink; leaving it unchanged." >&2
  else
    ln -s /Applications "$APPLICATIONS_LINK"
  fi
fi

if [[ "${MXU_OPEN_INSTALL_WINDOW:-1}" != "0" ]]; then
  open "$OUTPUT_PARENT"
  echo "Opened install window: drag $OUTPUT_NAME onto Applications."
fi
