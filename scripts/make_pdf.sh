#!/usr/bin/env bash
# make_pdf.sh <packet_dir> : cv.md -> cv.pdf (needs pandoc + a PDF engine)
set -euo pipefail
cd "$1"
pandoc cv.md -o cv.pdf -V papersize=a4 -V geometry:margin=2cm \
  --pdf-engine="${PDF_ENGINE:-weasyprint}"
