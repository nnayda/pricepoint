#!/bin/bash
# Resilient rsync to NFS — remounts and retries on disconnect
# Usage: sudo SRC="/path/to/redfin_part_*" NFS_SERVER=nfs.example.com ./rsync_redfin.sh

set -euo pipefail

SRC="${SRC:?set SRC to the local Redfin HTML glob to sync}"
MOUNT_POINT="${MOUNT_POINT:-/Volumes/redfin}"
NFS_SERVER="${NFS_SERVER:?set NFS_SERVER to the NFS host}"
NFS_EXPORT="${NFS_EXPORT:-/redfin}"
NFS_OPTS="vers=4.1,resvport"
MAX_RETRIES=50
RETRY_DELAY=5

unmount_nfs() {
    echo "[$(date)] Unmounting ${MOUNT_POINT}..."
    umount -f "$MOUNT_POINT" 2>/dev/null || true
    sleep 2
    # Kill any stale NFS processes holding the mount
    if mount | grep -q "$MOUNT_POINT"; then
        diskutil unmount force "$MOUNT_POINT" 2>/dev/null || true
        sleep 2
    fi
}

mount_nfs() {
    echo "[$(date)] Mounting ${NFS_SERVER}:${NFS_EXPORT} -> ${MOUNT_POINT}..."
    mkdir -p "$MOUNT_POINT"
    mount -t nfs -o "$NFS_OPTS" "${NFS_SERVER}:${NFS_EXPORT}" "$MOUNT_POINT"
    echo "[$(date)] Mounted successfully."
}

do_rsync() {
    echo "[$(date)] Starting rsync..."
    rsync -avh --progress --partial --no-times $SRC "$MOUNT_POINT/"
}

attempt=0
while true; do
    attempt=$((attempt + 1))

    if [ "$attempt" -gt "$MAX_RETRIES" ]; then
        echo "[$(date)] Exceeded ${MAX_RETRIES} retries. Giving up."
        exit 1
    fi

    echo ""
    echo "=========================================="
    echo "[$(date)] Attempt ${attempt}/${MAX_RETRIES}"
    echo "=========================================="

    # Ensure clean mount
    unmount_nfs
    mount_nfs

    if do_rsync; then
        echo ""
        echo "[$(date)] All files synced successfully!"
        exit 0
    else
        echo "[$(date)] rsync failed (NFS likely disconnected). Retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
    fi
done
