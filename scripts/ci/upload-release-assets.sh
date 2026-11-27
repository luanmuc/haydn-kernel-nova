#!/usr/bin/env bash
# 把正式 Release 的额外资产统一上传到已存在的 GitHub Release。
#
# 用法：
#   GITHUB_TOKEN=... REPO=luanmuc/haydn-kernel-nova \
#     bash scripts/ci/upload-release-assets.sh <release_id> <assets_dir>
#
# 目录内所有普通文件都会上传；已存在同名资产会跳过。
set -euo pipefail
umask 077

RID="${1:?用法: upload-release-assets.sh <release_id> <assets_dir>}"
ASSETS_DIR="${2:?用法: upload-release-assets.sh <release_id> <assets_dir>}"
[ -d "$ASSETS_DIR" ] || { echo "资产目录不存在: $ASSETS_DIR" >&2; exit 1; }

REPO="${REPO:-luanmuc/haydn-kernel-nova}"
TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.git-credentials" ]; then
  TOKEN=$(sed -n 's#https://[^:]*:\([^@]*\)@github.com#\1#p' "$HOME/.git-credentials" | head -1)
fi
[ -n "$TOKEN" ] || { echo "没有 GitHub 令牌" >&2; exit 1; }

API="https://api.github.com/repos/$REPO/releases/$RID/assets"
UPLOAD="https://uploads.github.com/repos/$REPO/releases/$RID/assets"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

curl --http1.1 -fsSL -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "$API" > "$TMPDIR/existing.json"
python3 - "$TMPDIR/existing.json" > "$TMPDIR/existing-names.txt" <<'PY'
import json,sys
for a in json.load(open(sys.argv[1])):
    print(a["name"])
PY

upload_asset() {
  local file="$1" name="$2" ctype="$3"
  local enc size code
  enc=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$name")
  size=$(stat -c %s "$file")
  echo "upload: $name ($size bytes)"
  code=$(curl --http1.1 -sS -o "$TMPDIR/asset.json" -w "%{http_code}" \
    -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
    -H "Content-Type: $ctype" --data-binary @"$file" \
    "$UPLOAD?name=$enc")
  [ "$code" = "201" ] || {
    echo "上传失败（HTTP $code）: $name" >&2
    cat "$TMPDIR/asset.json" >&2 || true
    exit 1
  }
  python3 - "$TMPDIR/asset.json" "$size" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
size=int(sys.argv[2])
if int(d.get("size",-1)) != size:
    raise SystemExit(f"上传后大小不一致: 远端 {d.get('size')} / 本地 {size}")
print("  ok", d["id"], d["name"], d["size"], d["state"])
PY
}

while IFS= read -r -d '' file; do
  name=$(basename "$file")
  if grep -Fxq "$name" "$TMPDIR/existing-names.txt"; then
    echo "skip existing: $name"
    continue
  fi
  case "$name" in
    *.md) ctype="text/markdown" ;;
    *.txt|*.log) ctype="text/plain" ;;
    *.img|*.bin|Image-*) ctype="application/octet-stream" ;;
    *.zip) ctype="application/zip" ;;
    *) ctype="application/octet-stream" ;;
  esac
  upload_asset "$file" "$name" "$ctype"
  echo "$name" >> "$TMPDIR/existing-names.txt"
done < <(find "$ASSETS_DIR" -maxdepth 1 -type f -print0 | sort -z)

echo "=== 额外资产上传完成：release $RID ==="
