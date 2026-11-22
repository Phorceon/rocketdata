#!/usr/bin/env bash
# Download the OpenRocket 24.12 JAR into lib/ (gitignored).
set -euo pipefail
cd "$(dirname "$0")/.."

JAAR="lib/OpenRocket.jar"
VERSION="24.12"
URL="https://github.com/openrocket/openrocket/releases/download/release-${VERSION}/OpenRocket-${VERSION}.jar"
SHA256="4959b72f52f5f607941e9722abbb7b7f0c4a38ebbbf84204a329db9f31c4f897"

mkdir -p lib
if [ -f "$JAAR" ] && [ "$(shasum -a 256 "$JAAR" | awk '{print $1}')" = "$SHA256" ]; then
  echo "already present: $JAAR"
  exit 0
fi

echo "downloading OpenRocket ${VERSION} -> $JAAR"
curl -sL -o "$JAAR" "$URL"

GOT="$(shasum -a 256 "$JAAR" | awk '{print $1}')"
if [ "$GOT" != "$SHA256" ]; then
  echo "checksum mismatch: expected $SHA256 got $GOT" >&2
  exit 1
fi
echo "ok: $JAAR"
