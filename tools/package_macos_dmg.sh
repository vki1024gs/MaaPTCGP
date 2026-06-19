#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: tools/package_macos_dmg.sh <install_dir> <output_dmg> <version> [app_name] [bundle_id]" >&2
  exit 1
fi

INSTALL_DIR="$1"
OUTPUT_DMG="$2"
FULL_VERSION="$3"
APP_NAME="${4:-MaaPTCGP}"
BUNDLE_ID="${5:-io.github.vki1024gs.maaptcgp}"

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

if [[ ! -f "$ICON_SOURCE" ]]; then
  echo "Missing icon source: $ICON_SOURCE" >&2
  exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "Missing create-dmg. Install it with: brew install create-dmg" >&2
  exit 1
fi

OUTPUT_DIR="$(dirname "$OUTPUT_DMG")"
OUTPUT_NAME="$(basename "$OUTPUT_DMG")"
mkdir -p "$OUTPUT_DIR"
OUTPUT_PATH="$(cd "$OUTPUT_DIR" && pwd)/$OUTPUT_NAME"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

pushd "$WORK_DIR" >/dev/null

mkdir "$APP_NAME.iconset"
sips -z 16 16     "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_16x16.png"
sips -z 32 32     "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_16x16@2x.png"
sips -z 32 32     "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_32x32.png"
sips -z 64 64     "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_32x32@2x.png"
sips -z 128 128   "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_128x128.png"
sips -z 256 256   "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_128x128@2x.png"
sips -z 256 256   "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_256x256.png"
sips -z 512 512   "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_256x256@2x.png"
sips -z 512 512   "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_512x512.png"
sips -z 1024 1024 "$ICON_SOURCE" --out "$APP_NAME.iconset/icon_512x512@2x.png"
iconutil -c icns "$APP_NAME.iconset" -o app.icns

APP_BUNDLE="$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
cp app.icns "$APP_BUNDLE/Contents/Resources/"
cp -R "$INSTALL_DIR/." "$APP_BUNDLE/Contents/MacOS/"

SHORT_VERSION="$(echo "$FULL_VERSION" | sed -E 's/^v//' | sed -E 's/-.*//')"

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
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

codesign --force --deep --sign - "$APP_BUNDLE"

mkdir dmg-root
cp -R "$APP_BUNDLE" dmg-root/
rm -f "$OUTPUT_PATH"

create-dmg \
  --volname "$APP_NAME Installer" \
  --volicon "app.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "$APP_BUNDLE" 200 190 \
  --hide-extension "$APP_BUNDLE" \
  --app-drop-link 600 185 \
  "$OUTPUT_PATH" \
  "dmg-root"

popd >/dev/null
