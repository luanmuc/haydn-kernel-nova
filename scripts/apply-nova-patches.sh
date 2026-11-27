#!/usr/bin/env bash
# Apply the ordered downstream patch series for haydn/nova-builtin-new.
#
# This script is intentionally strict: a patch that fails `git apply --check`
# is a build-stopping error, not something to silently skip.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
patch_dir="$repo_root/patches/nova/builtin-new"
series="$patch_dir/series"
audit="$patch_dir/UPSTREAM_AUDIT.yaml"
ksu="$repo_root/KernelSU"
check_only=0

if [ "${1:-}" = "--check" ]; then
  check_only=1
elif [ "$#" -ne 0 ]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

if [ ! -d "$patch_dir" ]; then
  echo "no builtin-new patch dir; skip (legacy patches/nova/5.4 is obsolete)"
  exit 0
fi

if [ ! -d "$ksu" ]; then
  echo "ERROR: KernelSU submodule is missing: $ksu" >&2
  exit 1
fi

if ! git -C "$ksu" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: KernelSU is not a git checkout (submodule not initialized?)" >&2
  exit 1
fi

if [ ! -f "$ksu/kernel/Kconfig" ]; then
  echo "ERROR: KernelSU submodule is empty: $ksu/kernel/Kconfig is missing" >&2
  exit 1
fi

if [ ! -f "$series" ]; then
  echo "ERROR: missing patch series: $series" >&2
  exit 1
fi

if [ ! -f "$audit" ]; then
  echo "ERROR: missing upstream audit: $audit" >&2
  exit 1
fi

actual_commit="$(git -C "$ksu" rev-parse HEAD)"
audited_commit="$(
  sed -n 's/^audited_submodule_commit:[[:space:]]*//p' "$audit" |
    head -n 1 |
    tr -d '"' |
    tr -d "'"
)"
audited_commit="${audited_commit%%[[:space:]]*}"

if [ -z "$audited_commit" ]; then
  echo "ERROR: audited_submodule_commit is empty in $audit" >&2
  exit 1
fi

if [ "$actual_commit" != "$audited_commit" ]; then
  echo "ERROR: KernelSU submodule changed without a fresh audit." >&2
  echo "  audited: $audited_commit" >&2
  echo "  actual : $actual_commit" >&2
  echo "Inspect upstream changes for every active patch, then update" >&2
  echo "$audit before building." >&2
  exit 1
fi

echo "KernelSU audit commit OK: $actual_commit"

# Every .patch in this directory must be active in series; a patch left on
# disk but omitted from series would otherwise be silently unused.
for patch_file in "$patch_dir"/*.patch; do
  [ -e "$patch_file" ] || continue
  base="$(basename "$patch_file")"
  if ! grep -qxF "$base" "$series"; then
    echo "ERROR: patch exists but is not listed in series: $base" >&2
    echo "Add it to series, or remove the patch file after retirement." >&2
    exit 1
  fi
done

count=0
declare -A seen_patches=()
while IFS= read -r raw_line || [ -n "$raw_line" ]; do
  line="${raw_line%%#*}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"

  [ -z "$line" ] && continue

  case "$line" in
    */*)
      echo "ERROR: series entries must be bare file names: $line" >&2
      exit 1
      ;;
    *.patch) ;;
    *)
      echo "ERROR: series entry is not a .patch file: $line" >&2
      exit 1
      ;;
  esac

  if [ -n "${seen_patches[$line]:-}" ]; then
    echo "ERROR: duplicate patch in series: $line" >&2
    exit 1
  fi
  seen_patches["$line"]=1

  patch="$patch_dir/$line"
  case_file="$patch_dir/cases/${line%.patch}.md"
  patch_id="${line%.patch}"

  if [ ! -f "$patch" ]; then
    echo "ERROR: patch listed in series is missing: $patch" >&2
    exit 1
  fi

  if [ ! -f "$case_file" ]; then
    echo "ERROR: patch has no case file: $case_file" >&2
    exit 1
  fi

  if ! grep -Fq "  ${patch_id}:" "$audit"; then
    echo "ERROR: patch has no entry in UPSTREAM_AUDIT.yaml: $patch_id" >&2
    exit 1
  fi

  if git -C "$ksu" apply --reverse --check "$patch" >/dev/null 2>&1; then
    echo "already applied: $line"
    count=$((count + 1))
    continue
  fi

  if ! git -C "$ksu" apply --check "$patch"; then
    echo "ERROR: patch does not apply cleanly: $line" >&2
    echo "This is NOT treated as 'already applied'. Inspect upstream changes," >&2
    echo "rebuild the patch if needed, and update UPSTREAM_AUDIT.yaml." >&2
    exit 1
  fi

  if [ "$check_only" -eq 1 ]; then
    echo "would apply: $line"
  else
    echo "applying: $line"
    git -C "$ksu" apply "$patch"
  fi

  count=$((count + 1))
done < "$series"

if [ "$count" -eq 0 ]; then
  echo "WARNING: no active patches in $series"
else
  echo "patch series OK: $count patch(es)"
fi
