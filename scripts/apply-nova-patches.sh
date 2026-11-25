#!/usr/bin/env bash
# Apply Nova 5.4 compatibility patches to the pinned SukiSU-Nova submodule.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
patch_dir="$repo_root/patches/nova/builtin-new"
if [ ! -d "$patch_dir" ]; then
  echo "no builtin-new patch dir; skip (legacy patches/nova/5.4 is obsolete)"
  exit 0
fi
for patch in "$patch_dir"/*.patch; do
  [ -e "$patch" ] || continue
  if git -C "$repo_root/KernelSU" apply --check "$patch" 2>/dev/null; then
    echo "applying $(basename "$patch")"
    git -C "$repo_root/KernelSU" apply "$patch"
  else
    echo "skip $(basename "$patch") (already applied or conflicting)"
  fi
done
