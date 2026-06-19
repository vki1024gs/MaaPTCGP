#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MXU="$ROOT/install/MaaPTCGP"

pkill -f "$MXU" 2>/dev/null || true
sleep 1
open "$MXU"

