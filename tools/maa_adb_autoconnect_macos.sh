#!/bin/sh

# Register BlueStacks' dynamically assigned local ADB endpoint before MXU asks
# MaaFramework to discover ADB devices. This intentionally inspects only sockets
# owned by a verified BlueStacks.app main process; it never scans host ports.

set -u

dry_run=0
if [ "${1:-}" = "--dry-run" ]; then
    dry_run=1
elif [ "$#" -ne 0 ]; then
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

if [ "$(/usr/bin/uname -s)" != "Darwin" ]; then
    exit 0
fi

if [ ! -x /usr/bin/pgrep ] || [ ! -x /usr/sbin/lsof ]; then
    echo "[adb-pretask] macOS process inspection tools are unavailable; skipped." >&2
    exit 0
fi

found_process=0
found_candidate=0
seen_endpoints=""

for pid in $(/usr/bin/pgrep -x BlueStacks 2>/dev/null); do
    case "$pid" in
        ''|*[!0-9]*) continue ;;
    esac

    process_path=$(/usr/sbin/lsof -nP -a -p "$pid" -d txt -Fn 2>/dev/null \
        | /usr/bin/sed -n 's/^n//p' \
        | /usr/bin/head -n 1)

    case "$process_path" in
        */BlueStacks.app/Contents/MacOS/BlueStacks)
            ;;
        *)
            continue
            ;;
    esac

    adb_path=${process_path%/BlueStacks}/hd-adb
    if [ ! -x "$adb_path" ]; then
        echo "[adb-pretask] Verified BlueStacks pid $pid, but its hd-adb is unavailable; skipped." >&2
        continue
    fi
    found_process=1

    listeners=$(/usr/sbin/lsof -nP -a -p "$pid" -iTCP -sTCP:LISTEN -Fn 2>/dev/null \
        | /usr/bin/sed -n 's/^n//p')
    for listener in $listeners; do
        case "$listener" in
            127.0.0.1:*|0.0.0.0:*|\*:*) port=${listener##*:} ;;
            \[::1\]:*|\[::\]:*) port=${listener##*:} ;;
            *) continue ;;
        esac
        case "$port" in
            ''|*[!0-9]*) continue ;;
        esac

        endpoint="127.0.0.1:$port"
        case " $seen_endpoints " in
            *" $endpoint "*) continue ;;
        esac
        seen_endpoints="$seen_endpoints $endpoint"
        found_candidate=1

        if [ "$dry_run" -eq 1 ]; then
            echo "[adb-pretask] candidate $endpoint (pid $pid, $adb_path)"
            continue
        fi

        result=$("$adb_path" connect "$endpoint" 2>&1)
        case "$result" in
            *"connected to $endpoint"*|*"already connected to $endpoint"*)
                echo "[adb-pretask] registered BlueStacks ADB endpoint $endpoint"
                ;;
        esac
    done
done

if [ "$dry_run" -eq 1 ]; then
    if [ "$found_process" -eq 0 ]; then
        echo "[adb-pretask] no verified running BlueStacks process found."
    elif [ "$found_candidate" -eq 0 ]; then
        echo "[adb-pretask] BlueStacks has no eligible local TCP listeners."
    fi
fi

# Absence of BlueStacks is normal. Do not prevent MXU from trying other ADB
# devices or reporting its own connection result.
exit 0
