#!/bin/sh

# Prepare a supported macOS emulator's ADB in three progressively stronger stages:
#   1. inspect verified emulator processes, endpoints, and device state;
#   2. connect only missing endpoints;
#   3. if that fails, rebuild only the verified emulator ADB server.
#
# Emulator endpoints are discovered only from TCP listeners owned by a
# verified, explicitly supported emulator process. The script never scans host
# ports and never assumes a fixed emulator port. This is an automatic MXU
# pretask: it is fully non-interactive, never opens a terminal, never waits for
# user input, and bounds every operation that can block.

set -u
exec </dev/null

# Healthy commands normally finish immediately. These stage-specific values
# are only upper bounds for a hung ADB process or a contended repair.
DEVICE_QUERY_TIMEOUT_SECONDS=1
CONNECT_TIMEOUT_SECONDS=1.5
REPAIR_LOCK_ATTEMPTS=10
SERVER_READY_ATTEMPTS=15
ADB_SERVER_PORT="${ADB_SERVER_PORT:-5037}"
ADB_LOG="${TMPDIR:-/private/tmp}/MaaPTCGP-emulator-adb.log"
LOCK_DIR="${TMPDIR:-/private/tmp}/MaaPTCGP-emulator-adb-repair.lock"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
elif [ "$#" -ne 0 ]; then
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

if [ "$(/usr/bin/uname -s)" != "Darwin" ]; then
    exit 0
fi

case "$ADB_SERVER_PORT" in
    ''|*[!0-9]*)
        echo "[adb-pretask] invalid ADB server port: $ADB_SERVER_PORT" >&2
        exit 2
        ;;
esac
if [ "$ADB_SERVER_PORT" -lt 1 ] || [ "$ADB_SERVER_PORT" -gt 65535 ]; then
    echo "[adb-pretask] invalid ADB server port: $ADB_SERVER_PORT" >&2
    exit 2
fi

for tool in /bin/kill /bin/rmdir /bin/sleep /usr/bin/awk /usr/bin/head /usr/bin/mktemp \
    /usr/bin/perl /usr/bin/pgrep /usr/bin/sed /usr/sbin/lsof; do
    if [ ! -x "$tool" ]; then
        echo "[adb-pretask] required macOS tool is unavailable: $tool" >&2
        exit 1
    fi
done

WORK_DIR=$(/usr/bin/mktemp -d "${TMPDIR:-/private/tmp}/MaaPTCGP-adb.XXXXXX") || exit 1
ENDPOINTS_FILE="$WORK_DIR/endpoints"
DEVICES_FILE="$WORK_DIR/devices"
MISSING_FILE="$WORK_DIR/missing"
PROVIDERS_FILE="$WORK_DIR/providers"
LOCK_HELD=0

cleanup() {
    if [ "$LOCK_HELD" -eq 1 ] && [ -d "$LOCK_DIR" ]; then
        /bin/rm -f "$LOCK_DIR/pid"
        /bin/rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
    /bin/rm -rf "$WORK_DIR"
}
trap cleanup EXIT HUP INT TERM

# macOS does not include timeout(1). A high-resolution Perl alarm gives each
# ADB operation its own short deadline, including fractional seconds.
run_with_timeout() {
    seconds=$1
    shift
    /usr/bin/perl -MTime::HiRes=alarm -e '
        $seconds = shift @ARGV;
        $SIG{ALRM} = sub { kill "TERM", $pid if $pid; exit 124 };
        $pid = fork();
        die "fork failed: $!\n" unless defined $pid;
        if ($pid == 0) { exec @ARGV; die "exec failed: $!\n" }
        alarm($seconds);
        waitpid($pid, 0);
        alarm(0);
        exit($? == -1 ? 1 : $? >> 8);
    ' "$seconds" "$@"
}

append_unique_line() {
    value=$1
    file=$2
    if ! /usr/bin/awk -v value="$value" '$0 == value { found=1 } END { exit !found }' "$file"; then
        echo "$value" >> "$file"
    fi
}

: > "$ENDPOINTS_FILE"
: > "$PROVIDERS_FILE"
ADB_PATH=""
VERIFIED_PROCESS_COUNT=0

# Each adapter names one exact process, verifies its executable bundle shape,
# and resolves the vendor ADB relative to that executable. Supporting another
# emulator means adding one adapter call; the repair policy stays unchanged.
inspect_emulator() {
    process_name=$1
    provider_name=$2
    executable_suffix=$3
    adb_relative_path=$4

    for pid in $(/usr/bin/pgrep -x "$process_name" 2>/dev/null); do
        case "$pid" in
            ''|*[!0-9]*) continue ;;
        esac

        process_path=$(/usr/sbin/lsof -nP -a -p "$pid" -d txt -Fn 2>/dev/null \
            | /usr/bin/sed -n 's/^n//p' \
            | /usr/bin/head -n 1)
        case "$process_path" in
            *"$executable_suffix") ;;
            *) continue ;;
        esac

        process_dir=${process_path%/*}
        adb_path="$process_dir/$adb_relative_path"
        if [ ! -x "$adb_path" ]; then
            echo "[adb-pretask] verified $provider_name pid $pid, but its ADB executable is unavailable." >&2
            continue
        fi
        if [ -n "$ADB_PATH" ] && [ "$ADB_PATH" != "$adb_path" ]; then
            echo "[adb-pretask] different emulator ADB executables are active; refusing automatic repair." >&2
            return 1
        fi
        ADB_PATH=$adb_path
        VERIFIED_PROCESS_COUNT=$((VERIFIED_PROCESS_COUNT + 1))
        append_unique_line "$provider_name" "$PROVIDERS_FILE"

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
            append_unique_line "127.0.0.1:$port" "$ENDPOINTS_FILE"
        done
    done
}

inspect_emulator "BlueStacks" "BlueStacks" \
    "/BlueStacks.app/Contents/MacOS/BlueStacks" "hd-adb" || exit 1
inspect_emulator "MuMuEmulator" "MuMuPlayer Pro" \
    "/Contents/MacOS/MuMuEmulator" "tools/adb" || exit 1

if [ "$VERIFIED_PROCESS_COUNT" -eq 0 ] || [ -z "$ADB_PATH" ]; then
    echo "[adb-pretask] no verified supported macOS emulator process found; nothing to prepare."
    exit 0
fi

if [ ! -s "$ENDPOINTS_FILE" ]; then
    echo "[adb-pretask] the verified emulator has no eligible local TCP endpoint; automatic repair is not applicable." >&2
    exit 1
fi

endpoint_count=$(/usr/bin/awk 'END { print NR + 0 }' "$ENDPOINTS_FILE")
provider_count=$(/usr/bin/awk 'END { print NR + 0 }' "$PROVIDERS_FILE")
echo "[adb-pretask] check: $provider_count emulator provider(s), $VERIFIED_PROCESS_COUNT process(es), $endpoint_count endpoint(s)."

read_devices() {
    : > "$DEVICES_FILE"
    ADB_MDNS=0 run_with_timeout "$DEVICE_QUERY_TIMEOUT_SECONDS" \
        "$ADB_PATH" devices -l > "$DEVICES_FILE" 2>&1
}

# Connect instances concurrently. One slow endpoint therefore consumes one
# connect deadline, not that deadline multiplied by the instance count.
connect_endpoints() {
    endpoints_file=$1
    phase=$2
    pids_file="$WORK_DIR/connect-pids"
    : > "$pids_file"

    while IFS= read -r endpoint; do
        [ -n "$endpoint" ] || continue
        (
            if ! ADB_MDNS=0 run_with_timeout "$CONNECT_TIMEOUT_SECONDS" \
                "$ADB_PATH" connect "$endpoint"; then
                echo "[adb-pretask] $phase: connect failed or timed out for $endpoint." >&2
                exit 1
            fi
        ) &
        echo "$!" >> "$pids_file"
    done < "$endpoints_file"

    failed=0
    while IFS= read -r connect_pid; do
        [ -n "$connect_pid" ] || continue
        wait "$connect_pid" || failed=1
    done < "$pids_file"
    return "$failed"
}

find_missing_endpoints() {
    : > "$MISSING_FILE"
    while IFS= read -r endpoint; do
        [ -n "$endpoint" ] || continue
        if ! /usr/bin/awk -v target="$endpoint" \
            '$1 == target && $2 == "device" { found=1 } END { exit !found }' "$DEVICES_FILE"; then
            echo "$endpoint" >> "$MISSING_FILE"
        fi
    done < "$ENDPOINTS_FILE"
}

if read_devices; then
    find_missing_endpoints
    if [ ! -s "$MISSING_FILE" ]; then
        echo "[adb-pretask] healthy: all discovered emulator ADB endpoints are already usable."
        exit 0
    fi
else
    /bin/cp "$ENDPOINTS_FILE" "$MISSING_FILE"
    echo "[adb-pretask] check: ADB device query failed or timed out; starting small repair." >&2
fi

if [ "$DRY_RUN" -eq 1 ]; then
    while IFS= read -r endpoint; do
        [ -n "$endpoint" ] && echo "[adb-pretask] dry-run: would connect $endpoint"
    done < "$MISSING_FILE"
    echo "[adb-pretask] dry-run: strong repair would run only if connect and verification fail."
    exit 0
fi

# Small repair: do not touch the shared ADB server. Connect only endpoints that
# were not already in a usable device state, then verify the complete set.
echo "[adb-pretask] small repair: registering missing emulator endpoints."
connect_endpoints "$MISSING_FILE" "small repair" || true

if read_devices; then
    find_missing_endpoints
    if [ ! -s "$MISSING_FILE" ]; then
        echo "[adb-pretask] recovered: all emulator endpoints are usable after small repair."
        exit 0
    fi
    missing_count=$(/usr/bin/awk 'END { print NR + 0 }' "$MISSING_FILE")
    if [ "$missing_count" -lt "$endpoint_count" ]; then
        echo "[adb-pretask] partial recovery: an emulator endpoint is already in use; refusing shared ADB server reset." >&2
        /usr/bin/sed 's/^/[adb-pretask]   still unavailable: /' "$MISSING_FILE" >&2
        exit 1
    fi
fi

# Strong repair is serialized across MXU tabs. A second pretask waits briefly
# for the first doctor to finish, then rechecks before attempting anything.
acquire_repair_lock() {
    attempts=0
    while ! /bin/mkdir "$LOCK_DIR" 2>/dev/null; do
        lock_pid=""
        if [ -f "$LOCK_DIR/pid" ]; then
            IFS= read -r lock_pid < "$LOCK_DIR/pid" || lock_pid=""
        fi
        case "$lock_pid" in
            ''|*[!0-9]*) ;;
            *)
                if ! /bin/kill -0 "$lock_pid" 2>/dev/null; then
                    /bin/rm -f "$LOCK_DIR/pid"
                    /bin/rmdir "$LOCK_DIR" 2>/dev/null || true
                    continue
                fi
                ;;
        esac
        attempts=$((attempts + 1))
        if [ "$attempts" -ge "$REPAIR_LOCK_ATTEMPTS" ]; then
            echo "[adb-pretask] another ADB repair is still active; refusing concurrent reset." >&2
            return 1
        fi
        /bin/sleep 0.05
    done
    LOCK_HELD=1
    echo "$$" > "$LOCK_DIR/pid"
    return 0
}

acquire_repair_lock || exit 1

# The other tab may have repaired ADB while this invocation waited.
if read_devices; then
    find_missing_endpoints
    if [ ! -s "$MISSING_FILE" ]; then
        echo "[adb-pretask] recovered: another invocation repaired ADB."
        exit 0
    fi
    missing_count=$(/usr/bin/awk 'END { print NR + 0 }' "$MISSING_FILE")
    if [ "$missing_count" -lt "$endpoint_count" ]; then
        echo "[adb-pretask] partial recovery: another endpoint is usable; refusing shared ADB server reset." >&2
        exit 1
    fi
fi

echo "[adb-pretask] strong repair: rebuilding the verified emulator ADB server." >&2

# Stop only ADB processes whose executable text path is the exact verified
# vendor binary. Matching by basename merely narrows the candidates; the path
# comparison is the authorization check.
adb_executable_name=${ADB_PATH##*/}
for client_pid in $(/usr/bin/pgrep -x "$adb_executable_name" 2>/dev/null); do
    case "$client_pid" in
        ''|*[!0-9]*|"$$") continue ;;
    esac
    client_path=$(/usr/sbin/lsof -nP -a -p "$client_pid" -d txt -Fn 2>/dev/null \
        | /usr/bin/sed -n 's/^n//p' \
        | /usr/bin/head -n 1)
    if [ "$client_path" = "$ADB_PATH" ]; then
        /bin/kill "$client_pid" 2>/dev/null || true
    fi
done

server_pid=$(/usr/sbin/lsof -nP -tiTCP:"$ADB_SERVER_PORT" -sTCP:LISTEN 2>/dev/null \
    | /usr/bin/head -n 1)
if [ -n "$server_pid" ]; then
    server_path=$(/usr/sbin/lsof -nP -a -p "$server_pid" -d txt -Fn 2>/dev/null \
        | /usr/bin/sed -n 's/^n//p' \
        | /usr/bin/head -n 1)
    if [ "$server_path" != "$ADB_PATH" ]; then
        echo "[adb-pretask] port $ADB_SERVER_PORT belongs to another ADB executable; refusing to stop it." >&2
        exit 1
    fi
    /bin/kill "$server_pid" 2>/dev/null || true
    /bin/sleep 0.2
fi

# 5554 is below ADB's first automatic emulator probe port (5555), so this
# disables automatic probing without fixing or guessing any emulator endpoint.
# Every verified endpoint is connected explicitly after the server starts.
ADB_MDNS=0 ADB_LOCAL_TRANSPORT_MAX_PORT=5554 \
    /usr/bin/nohup "$ADB_PATH" server nodaemon </dev/null >> "$ADB_LOG" 2>&1 &
new_server_pid=$!

server_ready=0
attempts=0
while [ "$attempts" -lt "$SERVER_READY_ATTEMPTS" ]; do
    current_pid=$(/usr/sbin/lsof -nP -tiTCP:"$ADB_SERVER_PORT" -sTCP:LISTEN 2>/dev/null \
        | /usr/bin/head -n 1)
    if [ -n "$current_pid" ]; then
        current_path=$(/usr/sbin/lsof -nP -a -p "$current_pid" -d txt -Fn 2>/dev/null \
            | /usr/bin/sed -n 's/^n//p' \
            | /usr/bin/head -n 1)
        if [ "$current_path" = "$ADB_PATH" ]; then
            server_ready=1
            break
        fi
    fi
    if ! /bin/kill -0 "$new_server_pid" 2>/dev/null; then
        break
    fi
    attempts=$((attempts + 1))
    /bin/sleep 0.1
done

if [ "$server_ready" -ne 1 ]; then
    echo "[adb-pretask] strong repair failed to start ADB server; log: $ADB_LOG" >&2
    exit 1
fi

connect_endpoints "$ENDPOINTS_FILE" "strong repair" || true

if ! read_devices; then
    echo "[adb-pretask] strong repair completed, but ADB device verification failed." >&2
    exit 1
fi
find_missing_endpoints
if [ -s "$MISSING_FILE" ]; then
    echo "[adb-pretask] strong repair completed, but some emulator endpoints are not usable:" >&2
    /usr/bin/sed 's/^/[adb-pretask]   /' "$MISSING_FILE" >&2
    exit 1
fi

echo "[adb-pretask] recovered: all emulator endpoints are usable after strong repair."
exit 0
