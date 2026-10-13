#!/usr/bin/env bash
# Build the 2FAK Mouse Jiggler firmware from Git Bash, using the
# arm-none-eabi-gcc + make bundled with STM32CubeIDE.
# Builds in a space-free temp dir (the project path contains a space).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$HOME/jigglebuild"

GCC_BIN="$(ls -d /c/ST/STM32CubeIDE_*/STM32CubeIDE/plugins/*gnu-tools-for-stm32*/tools/bin 2>/dev/null | head -1)"
MAKE_BIN="$(ls -d /c/ST/STM32CubeIDE_*/STM32CubeIDE/plugins/*externaltools.make*/tools/bin 2>/dev/null | head -1)"
[ -n "$GCC_BIN" ] && [ -n "$MAKE_BIN" ] || { echo "STM32CubeIDE toolchain not found under C:\\ST" >&2; exit 1; }
export PATH="$GCC_BIN:$MAKE_BIN:$PATH"

echo ">> copying to $BUILD"
rm -rf "$BUILD"; mkdir -p "$BUILD"
cp -r "$REPO/." "$BUILD/"

cd "$BUILD"
make clean >/dev/null 2>&1 || true
make

mkdir -p "$REPO/prebuilt"
cp 2fak_jiggler.hex 2fak_jiggler.bin 2fak_jiggler.elf "$REPO/prebuilt/"
echo ">> DONE. Artifacts in: $REPO/prebuilt"
