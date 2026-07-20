#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: tools/rebuild_macos_app.sh <install_dir> <output_app> <version> [app_name] [bundle_id]" >&2
  echo "Example: tools/rebuild_macos_app.sh install build/MaaPTCGP.app v0.1.9" >&2
  exit 1
fi

INSTALL_DIR="$1"
OUTPUT_APP="$2"
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
  ICONSET="$WORK_DIR/$APP_NAME.iconset"
  mkdir "$ICONSET"
  sips -z 16 16     "$ICON_SOURCE" --out "$ICONSET/icon_16x16.png" >/dev/null
  sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET/icon_32x32.png" >/dev/null
  sips -z 64 64     "$ICON_SOURCE" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   "$ICON_SOURCE" --out "$ICONSET/icon_128x128.png" >/dev/null
  sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET/icon_256x256.png" >/dev/null
  sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
  if iconutil -c icns "$ICONSET" -o "$APP_BUNDLE/Contents/Resources/app.icns" 2>/dev/null; then
    ICON_PLIST_ENTRY=$'    <key>CFBundleIconFile</key>\n    <string>app.icns</string>'
  else
    echo "Warning: failed to build app icon; continuing without CFBundleIconFile." >&2
    rm -f "$APP_BUNDLE/Contents/Resources/app.icns"
  fi
fi

# Use ditto without extended attributes/resource forks so downloaded quarantine
# metadata from source files is not carried into the locally rebuilt app.
ditto --noextattr --norsrc "$INSTALL_DIR" "$APP_BUNDLE/Contents/MacOS"

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
