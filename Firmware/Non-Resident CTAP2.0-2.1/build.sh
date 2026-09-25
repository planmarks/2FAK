#!/usr/bin/env bash
# Build the 2FA Key firmware (Nitrokey FIDO2 fork) on Windows, from Git Bash,
# using the arm-none-eabi-gcc + make bundled with STM32CubeIDE.
#
# Handles two Windows/native-make quirks discovered during bring-up:
#   * the project path contains a space -> build in a space-free temp dir
#   * the ST make.exe $(shell ...) fails under sh -> pass version vars explicitly
#
# Output: bootloader.hex, solo.hex (+ .elf/.bin) copied into ./prebuilt/
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$HOME/2fakey-build/fw"          # $HOME = /c/Users/<you> (no spaces)

# 1. Locate the CubeIDE-bundled toolchain (version-agnostic globs)
GCC_BIN="$(ls -d /c/ST/STM32CubeIDE_*/STM32CubeIDE/plugins/*gnu-tools-for-stm32*/tools/bin 2>/dev/null | head -1)"
MAKE_BIN="$(ls -d /c/ST/STM32CubeIDE_*/STM32CubeIDE/plugins/*externaltools.make*/tools/bin 2>/dev/null | head -1)"
if [ -z "$GCC_BIN" ] || [ -z "$MAKE_BIN" ]; then
  echo "ERROR: STM32CubeIDE toolchain (gcc/make) not found under C:\\ST" >&2; exit 1
fi

# 2. Fresh copy into a space-free path
echo ">> copying source to $BUILD"
rm -rf "$BUILD"; mkdir -p "$BUILD"
cp -r "$REPO/." "$BUILD/"

# 3. python3 shim (Windows only ships 'python') + toolchain on PATH
mkdir -p "$BUILD/shim"
printf '#!/bin/sh\nexec python "$@"\n' > "$BUILD/shim/python3"; chmod +x "$BUILD/shim/python3"
export PATH="$GCC_BIN:$MAKE_BIN:$BUILD/shim:$PATH"

# 4. Version is normally derived from a git tag via $(shell); that path is broken
#    with the native make, so we pass the version explicitly. Change here to bump.
VER=5.0.0
VARS="VERSION=$VER VERSION_FULL=$VER VERSION_FULL_RAW=$VER.nitrokey \
VERSION_MAJ=${VER%%.*} VERSION_MIN=0 VERSION_PAT=0 \
SOLO_VERSION_FULL=$VER SOLO_VERSION=$VER SOLO_VERSION_MAJ=${VER%%.*} \
SOLO_VERSION_MIN=0 SOLO_VERSION_PAT=0 PAGESHR=256kB"

# Optional: PROVISION=1 builds the one-time ATECC provisioning image. It enables the
# button-gated CTAPHID_ATECC_PROVISION command and goes to prebuilt/provision/ so it
# never overwrites the normal all.hex. Flash it ONLY to a sacrificial unit.
if [ "${PROVISION:-0}" = "1" ]; then
  VARS="$VARS PROVISION_DEFINE=-DATECC_PROVISION"
  OUT="$REPO/prebuilt/provision"
  echo ">> PROVISION build (ATECC provisioning enabled) -> $OUT"
else
  OUT="$REPO/prebuilt"
fi

# CTAP1/U2F is legacy-only and OFF by default to save flash. U2F=1 includes it.
if [ "${U2F:-0}" = "1" ]; then
  VARS="$VARS CTAP1_DEFINE=-DCTAP1_ENABLED"
  echo ">> U2F/CTAP1 legacy support ENABLED"
fi

# PIN enforcement policy. Default: optional (RP decides). Set PIN_POLICY=requireset to
# force a PIN to be set before the first credential, or PIN_POLICY=alwaysuv to require
# PIN/UV on every makeCredential and getAssertion.
case "${PIN_POLICY:-optional}" in
  requireset) VARS="$VARS PIN_POLICY_DEFINE=-DPIN_POLICY=1"; echo ">> PIN policy: require PIN set";;
  alwaysuv)   VARS="$VARS PIN_POLICY_DEFINE=-DPIN_POLICY=2"; echo ">> PIN policy: alwaysUv (force PIN/UV)";;
  optional|"") ;;  # default, no define
  *) echo "ERROR: PIN_POLICY must be optional | requireset | alwaysuv" >&2; exit 1;;
esac

# CTAP version advertised. Default tops out at FIDO_2_1 (what we conform to). FIDO23=1
# additionally advertises FIDO_2_3 (only once full 2.3 conformance is validated).
if [ "${FIDO23:-0}" = "1" ]; then
  VARS="$VARS FIDO23_DEFINE=-DADVERTISE_FIDO_2_3"
  echo ">> Advertising FIDO_2_3 (ensure conformance before shipping)"
fi

# Resident (passkey) features. This is the NON-RESIDENT second-factor SKU, so RESIDENT
# defaults to 0 (rk=false, no credMgmt, rk=true rejected). Set RESIDENT=1 only for the
# passkey firmware (which lives in ../Resident CTAP2.3).
if [ "${RESIDENT:-0}" = "1" ]; then
  VARS="$VARS RESIDENT_DEFINE=-DRESIDENT_KEYS"
  echo ">> Resident/passkey features ENABLED (rk + credMgmt)"
else
  echo ">> Non-resident second-factor build (no rk / credMgmt)"
fi

# CONFORMANCE=1 relaxes test-hostile behaviours for the FIDO conformance tools:
# authenticatorReset is allowed any time (not just within 10s of power-up), so the tool
# can reset programmatically between test groups. NOT for production images.
if [ "${CONFORMANCE:-0}" = "1" ]; then
  VARS="$VARS CONFORMANCE_DEFINE=-DCONFORMANCE_BUILD"
  echo ">> CONFORMANCE build (reset allowed any time) - do not ship"
fi

# Bootloader flavour:
#   VERIFY_BOOT=0 (default): non-verifying (DEV) bootloader - accepts UNSIGNED firmware
#     over USB. For development/testing only.
#   VERIFY_BOOT=1: verifying (PRODUCTION) bootloader - accepts firmware over USB only if
#     signed with the muru production key (secrets/bootloader/bootloader-prod.pem, public
#     half embedded in bootloader/pubkey_bootloader.c). Required before the SWD/RDP-2
#     lockdown so units remain updatable over USB after SWD is closed.
if [ "${VERIFY_BOOT:-0}" = "1" ]; then
  BOOT_TARGET="bootloader-verifying"
  IMG_TAG="verifying"
  # RELEASE=1 makes the Makefile drop -DNK_TEST_MODE, so pubkey_bootloader.c selects the
  # PRODUCTION key branch (our muru key) instead of the Nitrokey test key. Without this the
  # verifying bootloader embeds the test key and rejects our signatures.
  # Also drop -DSOLO_HACKER from the app: production images are not "hacker" builds.
  VARS="$VARS RELEASE=1 SOLO_HACKER_DEFINE="
  echo ">> Bootloader: VERIFYING (production; RELEASE=1 -> our key; SOLO_HACKER off)"
else
  BOOT_TARGET="bootloader-nonverifying"
  IMG_TAG="dev"
  echo ">> Bootloader: non-verifying (dev, unsigned USB updates)"
fi

cd "$BUILD/targets/stm32l432"
echo ">> make cbor";                  make cbor                  $VARS
echo ">> make $BOOT_TARGET";          make $BOOT_TARGET          $VARS
# The bootloader build compiles the shared fido2/crypto/src objects WITH
# -DIS_BOOTLOADER. Remove them so the app (all-hacker) recompiles them without it;
# otherwise the app can link a bootloader-flavoured object (e.g. ctaphid.o -> the
# guarded bootloader_bridge reference) and fail. Mirrors the Makefile build-hacker
# flow, which runs `clean` between the two builds.
echo ">> clean shared objects between bootloader and app builds"
rm -f *.o src/*.o bootloader/*.o \
      ../../fido2/*.o ../../fido2/extensions/*.o \
      ../../crypto/sha256/*.o ../../crypto/micro-ecc/*.o \
      ../../crypto/tiny-AES-c/*.o ../../crypto/cifra/src/*.o 2>/dev/null || true
echo ">> make all-hacker";            make all-hacker            $VARS

# 5. Collect artifacts (tagged dev/verifying so both flavours can coexist)
mkdir -p "$OUT"
cp solo.hex solo.bin solo.elf "$OUT/"
cp bootloader.hex "$OUT/bootloader-$IMG_TAG.hex"
cp bootloader.elf "$OUT/bootloader-$IMG_TAG.elf"

# 6. Build the flashable merged image (app + bootloader + boot auth word +
#    seeded hacker attestation key). Regenerate every build so it is never stale.
#    all-dev.hex       = non-verifying bootloader (unsigned USB updates)
#    all-verifying.hex = verifying bootloader (signed USB updates only)
echo ">> make_all.py -> $OUT/all-$IMG_TAG.hex"
( cd "$REPO" && python make_all.py "$OUT/solo.hex" "$OUT/bootloader-$IMG_TAG.hex" "$OUT/all-$IMG_TAG.hex" )

echo
echo ">> DONE. Artifacts in: $OUT"
"$GCC_BIN/arm-none-eabi-size" solo.elf bootloader.elf
