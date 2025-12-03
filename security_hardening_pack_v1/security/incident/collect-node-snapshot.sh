#!/usr/bin/env bash
set -euo pipefail
OUTDIR=${1:-/tmp/forensics-$(date +%Y%m%d%H%M%S)}
mkdir -p "$OUTDIR"
echo "Collecting ps aux..." > "$OUTDIR/ps.txt"
ps aux >> "$OUTDIR/ps.txt"
echo "Collecting network connections..." > "$OUTDIR/netstat.txt"
ss -tunap >> "$OUTDIR/netstat.txt"
echo "Collecting dmesg..." > "$OUTDIR/dmesg.txt"
dmesg >> "$OUTDIR/dmesg.txt"
echo "Snapshot saved to $OUTDIR"
