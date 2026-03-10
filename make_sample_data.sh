#!/usr/bin/env bash
# make_sample_data.sh — Create sample binary files for HTTP upload/SCP tests.
# Usage: bash make_sample_data.sh [output_dir]
# Output: sample_data/file_50mb.bin  sample_data/file_200mb.bin

set -euo pipefail

OUTDIR="${1:-sample_data}"
mkdir -p "$OUTDIR"

echo "Creating ${OUTDIR}/file_50mb.bin (50 MB)..."
dd if=/dev/urandom bs=1m count=50 of="${OUTDIR}/file_50mb.bin" 2>/dev/null
echo "  → done"

echo "Creating ${OUTDIR}/file_200mb.bin (200 MB)..."
dd if=/dev/urandom bs=1m count=200 of="${OUTDIR}/file_200mb.bin" 2>/dev/null
echo "  → done"

echo ""
echo "Sample files created:"
ls -lh "${OUTDIR}/"

echo ""
echo "To serve these files from the remote server for download tests:"
echo "  ssh <user>@<server> 'mkdir -p ~/http_files'"
echo "  scp ${OUTDIR}/file_200mb.bin <user>@<server>:~/http_files/"
echo "  ssh <user>@<server> 'cd ~/http_files && python3 -m http.server 8080 &'"
echo ""
echo "Then set in config.yaml:"
echo "  http_download:"
echo "    urls:"
echo "      - http://<server>:8080/file_200mb.bin"
