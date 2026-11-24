#!/usr/bin/env bash
# Offline preflight for a Nova AnyKernel3 zip.
# Usage: ./scripts/preflight-release.sh <package.zip> [haydn-config-used.txt]
set -euo pipefail

pkg=${1:?usage: preflight-release.sh <package.zip> [config.txt]}
config=${2:-}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "PASS: $*"; }

[ -f "$pkg" ] || fail "package not found: $pkg"
sha256sum "$pkg"
unzip -t "$pkg" >/dev/null || fail "zip integrity"
ok "zip integrity"

unzip -p "$pkg" anykernel.sh > "$work/anykernel.sh"
bash -n "$work/anykernel.sh" || fail "anykernel syntax"
grep -q '^block=boot$' "$work/anykernel.sh" || fail "AnyKernel block must be boot"
ok "AnyKernel syntax/block"
if grep -q '^do.devicecheck=0$' "$work/anykernel.sh"; then
  echo "WARN: do.devicecheck=0；刷入前必须人工确认设备为 haydn"
fi
grep -q 'do.modules=0' "$work/anykernel.sh" || fail "modules policy changed unexpectedly"
ok "no module packaging"

unzip -p "$pkg" Image > "$work/Image"
file "$work/Image" | grep -q 'Linux kernel ARM64 boot executable Image' || fail "Image format"
[ "$(dd if="$work/Image" bs=1 skip=56 count=4 2>/dev/null)" = "ARMd" ] || fail "ARM64 Image magic"
ok "ARM64 Image header"

strings -a "$work/Image" > "$work/strings.txt"
grep -q '5.4.302-HoshinoNeko-nova' "$work/strings.txt" || fail "Nova localversion missing"
grep -q 'susfs is initialized! version: v2.4.0' "$work/strings.txt" || fail "SUSFS v2.4.0 banner missing"
grep -q 'CMD_SUSFS_SET_SUS_PATH_UID_FILTER' "$work/strings.txt" || fail "SUSFS UID filter path missing"
grep -q 'CMD_SUSFS_SET_PRIORITY_UID_FILTER' "$work/strings.txt" || fail "SUSFS priority UID filter path missing"
ok "Nova/SUSFS identity strings"
if grep -qi 'bakasu' "$work/strings.txt"; then
  fail "BakaSU marker found in Nova Image"
fi
ok "no BakaSU marker"

if [ -n "$config" ]; then
  [ -f "$config" ] || fail "config not found: $config"
  for sym in CONFIG_KSU=y CONFIG_KSU_SUSFS=y CONFIG_THREAD_INFO_IN_TASK=y CONFIG_KPROBES=y \
             CONFIG_KSU_SUSFS_SUS_PATH=y CONFIG_KSU_SUSFS_SUS_MOUNT=y \
             CONFIG_KSU_SUSFS_SUS_KSTAT=y CONFIG_KSU_SUSFS_OPEN_REDIRECT=y \
             CONFIG_KSU_SUSFS_SUS_MAP=y CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y; do
    grep -q "^${sym}$" "$config" || fail "config missing: $sym"
  done
  grep -q '^CONFIG_LOCALVERSION="-HoshinoNeko-nova"' "$config" || fail "Nova CONFIG_LOCALVERSION missing"
  ok "effective config"
fi

echo "PREFLIGHT OK: $pkg"
