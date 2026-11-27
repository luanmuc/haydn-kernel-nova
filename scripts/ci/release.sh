#!/usr/bin/env bash
# 下载指定构建 run 的产物并发布 GitHub Release。
#
# 用法（建议在工作区根执行，仓库在 repo/ 下时自动识别 WORK_ROOT）：
#   bash scripts/ci/release.sh <tag> [release_name] [body_file]
#
# 可选环境变量：
#   RUN_ID=123456789       指定构建 run（默认读 $WORK_ROOT/tmp/ci-run-id.txt）
#   WORK_ROOT=/path        工作区根（默认：当前目录含 PROGRESS.md + repo/，否则仓库根）
#   REPO=owner/repo         覆盖仓库（默认本 fork）
#   GITHUB_TOKEN=...        覆盖令牌（默认只从 ~/.git-credentials 读取）
#   RELEASE_ASSETS_DIR=/path 额外资产目录；设置后统一上传其中文件
#   DRY_RUN=1               只做校验，不创建 Release、不上传资产
#
# 硬校验：
#   1) tag 必须已存在，并解析到真实 commit（annotated tag 会解引用）
#   2) 构建 run 必须 completed + success，且 head_sha 必须等于 tag commit
#   3) 产物 zip 名必须包含该 commit 的 9 位短 SHA
#   4) Release 已存在时拒绝覆盖（DRY_RUN 下只提示）
set -euo pipefail
umask 077

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="${REPO:-luanmuc/haydn-kernel-nova}"

usage() {
  sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

TAG="${1:?用法: release.sh <tag> [release_name] [body_file]}"
NAME="${2:-$TAG}"

if [ -z "${WORK_ROOT:-}" ]; then
  if [ -f "$PWD/PROGRESS.md" ] && [ -d "$PWD/repo" ]; then
    WORK_ROOT="$PWD"
  else
    WORK_ROOT="$REPO_ROOT"
  fi
fi

case "${3:-}" in
  "") BODY_FILE="${BODY_FILE:-$WORK_ROOT/tmp/release-body.md}" ;;
  /*) BODY_FILE="$3" ;;
  *)  BODY_FILE="$PWD/$3" ;;
esac

RUN_ID="${RUN_ID:-$(cat "$WORK_ROOT/tmp/ci-run-id.txt" 2>/dev/null || true)}"
DRY_RUN="${DRY_RUN:-0}"
OUT_DIR="$WORK_ROOT/tmp/release"
API="https://api.github.com/repos/$REPO"
UPLOAD_API="https://uploads.github.com/repos/$REPO"

fail() { echo "错误: $*" >&2; exit 1; }

[ -n "$RUN_ID" ] || fail "没有 RUN_ID；请设置 RUN_ID 或写 $WORK_ROOT/tmp/ci-run-id.txt"
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || fail "RUN_ID 不是数字: $RUN_ID"
[ -f "$BODY_FILE" ] || fail "Release 说明文件不存在: $BODY_FILE"

TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.git-credentials" ]; then
  TOKEN=$(sed -n 's#https://[^:]*:\([^@]*\)@github.com#\1#p' "$HOME/.git-credentials" | head -1)
fi
[ -n "$TOKEN" ] || fail "没有 GitHub 令牌：请设置 GITHUB_TOKEN 或配置 ~/.git-credentials"

mkdir -p "$OUT_DIR"
TAG_JSON="$OUT_DIR/tag.json"
RELEASE_JSON="$OUT_DIR/release.json"
RUN_JSON="$OUT_DIR/run.json"
ARTIFACTS_JSON="$OUT_DIR/artifacts.json"
ARTIFACT_JSON="$OUT_DIR/artifact.json"

api_get() {
  local url="$1" out="$2"
  curl -sS -o "$out" -w "%{http_code}" \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "$url"
}

echo "=== 0) 校验 tag ==="
HTTP=$(api_get "$API/git/ref/tags/$TAG" "$TAG_JSON")
[ "$HTTP" = "200" ] || fail "tag '$TAG' 不存在（HTTP $HTTP）。请先建 tag 并推送，再重跑。"
TAG_TYPE=$(python3 -c "import json;print(json.load(open('$TAG_JSON'))['object']['type'])")
TAG_OBJ=$(python3 -c "import json;print(json.load(open('$TAG_JSON'))['object']['sha'])")
if [ "$TAG_TYPE" = "tag" ]; then
  TAG_OBJ_JSON="$OUT_DIR/tag-object.json"
  HTTP=$(api_get "$API/git/tags/$TAG_OBJ" "$TAG_OBJ_JSON")
  [ "$HTTP" = "200" ] || fail "annotated tag 对象取不到（HTTP $HTTP）"
  COMMIT=$(python3 -c "import json;print(json.load(open('$TAG_OBJ_JSON'))['object']['sha'])")
else
  COMMIT="$TAG_OBJ"
fi
SHORT9="${COMMIT:0:9}"
echo "tag '$TAG' -> commit $COMMIT"

echo "=== 0b) 检查 Release 是否已存在 ==="
HTTP=$(api_get "$API/releases/tags/$TAG" "$RELEASE_JSON")
if [ "$HTTP" = "200" ]; then
  if [ "$DRY_RUN" = "1" ]; then
    echo "Release 已存在（DRY_RUN 只提示，不创建）"
  else
    fail "Release '$TAG' 已存在；拒绝覆盖。需要改说明请到网页编辑，或删旧 Release 后重跑。"
  fi
elif [ "$HTTP" != "404" ]; then
  fail "查询 Release 失败（HTTP $HTTP）"
fi

echo "=== 1) 校验构建 run ==="
HTTP=$(api_get "$API/actions/runs/$RUN_ID" "$RUN_JSON")
[ "$HTTP" = "200" ] || fail "构建 run $RUN_ID 不存在（HTTP $HTTP）"
read -r RUN_STATUS RUN_CONCLUSION RUN_HEAD < <(python3 - "$RUN_JSON" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print(r.get("status",""), r.get("conclusion",""), r.get("head_sha",""))
PY
)
[ "$RUN_STATUS" = "completed" ] || fail "run $RUN_ID 尚未完成（status=$RUN_STATUS）"
[ "$RUN_CONCLUSION" = "success" ] || fail "run $RUN_ID 结论不是 success（conclusion=$RUN_CONCLUSION）"
[ "$RUN_HEAD" = "$COMMIT" ] || fail "run $RUN_ID head_sha=$RUN_HEAD 与 tag commit=$COMMIT 不一致；拒绝发布错误产物"
echo "run $RUN_ID: success @ $RUN_HEAD"

echo "=== 2) 选择产物 ==="
HTTP=$(api_get "$API/actions/runs/$RUN_ID/artifacts" "$ARTIFACTS_JSON")
[ "$HTTP" = "200" ] || fail "取产物列表失败（HTTP $HTTP）"
python3 - "$ARTIFACTS_JSON" "$ARTIFACT_JSON" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
items=[a for a in d.get("artifacts",[]) if a.get("name","").startswith("HoshinoNeko-haydn-") and not a.get("expired")]
if not items:
    raise SystemExit("没有可用的 HoshinoNeko-haydn-* 产物")
items.sort(key=lambda a:a.get("created_at",""), reverse=True)
for a in items:
    print(a["id"], a["name"], a["size_in_bytes"], a.get("created_at",""))
json.dump(items[0], open(sys.argv[2],"w"))
PY
ART_ID=$(python3 -c "import json;print(json.load(open('$ARTIFACT_JSON'))['id'])")
ART_NAME=$(python3 -c "import json;print(json.load(open('$ARTIFACT_JSON'))['name'])")
echo "选中产物: $ART_NAME ($ART_ID)"

echo "=== 3) 下载并解压 ==="
curl -sSL -H "Authorization: token $TOKEN" "$API/actions/artifacts/$ART_ID/zip" -o "$OUT_DIR/artifact.zip"
rm -rf "$OUT_DIR/artifact" && mkdir -p "$OUT_DIR/artifact"
unzip -q -o "$OUT_DIR/artifact.zip" -d "$OUT_DIR/artifact"

ZIP=$(find "$OUT_DIR/artifact" -name 'HoshinoNeko_*_Any3Kernel.zip' | head -1)
IMAGE=$(find "$OUT_DIR/artifact" -name 'Image' | head -1)
[ -n "$ZIP" ] || fail "产物里没有 AnyKernel zip"
[ -n "$IMAGE" ] || fail "产物里没有 Image"
case "$(basename "$ZIP")" in
  *"_${SHORT9}_"*) ;;
  *) fail "zip 名 $(basename "$ZIP") 不含 commit 短 SHA $SHORT9，拒绝发布" ;;
esac
ZIP_SIZE=$(stat -c %s "$ZIP")
IMAGE_SIZE=$(stat -c %s "$IMAGE")
[ "$ZIP_SIZE" -gt 0 ] && [ "$IMAGE_SIZE" -gt 0 ] || fail "产物大小为 0"
AK_SCRIPT="$(unzip -p "$ZIP" anykernel.sh | tr -d '\r')"
grep -qE '^BLOCK=\$block$' <<<"$AK_SCRIPT" || fail "AnyKernel 未显式设置 BLOCK=\$block，拒绝发布"
grep -qE '^IS_SLOT_DEVICE=0$' <<<"$AK_SCRIPT" || fail "AnyKernel 未设置 IS_SLOT_DEVICE=0，拒绝发布"
if grep -qE '^(is_slot_device|ramdisk_compression|patch_vbmeta_flag|no_magisk_check)=' <<<"$AK_SCRIPT"; then
  fail "AnyKernel 仍含小写变量，TWRP 会无法识别分区，拒绝发布"
fi
echo "zip: $(basename "$ZIP") ($ZIP_SIZE 字节)"
echo "Image: $IMAGE_SIZE 字节"
echo "zip sha256: $(sha256sum "$ZIP" | awk '{print $1}')"

if [ "$DRY_RUN" = "1" ]; then
  echo "=== DRY_RUN=1：校验通过，停在创建 Release 前 ==="
  exit 0
fi

echo "=== 4) 创建 Release ==="
python3 - "$TAG" "$NAME" "$BODY_FILE" "$COMMIT" "$OUT_DIR/payload.json" <<'PY'
import json,sys
tag,name,body_file,commit,out=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
body=open(body_file,encoding="utf-8").read()
json.dump({"tag_name":tag,"name":name,"body":body,"target_commitish":commit,
           "draft":False,"prerelease":False}, open(out,"w",encoding="utf-8"), ensure_ascii=False)
PY
HTTP=$(curl -sS -o "$OUT_DIR/release-create.json" -w "%{http_code}" \
  -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "$API/releases" -d @"$OUT_DIR/payload.json")
[ "$HTTP" = "201" ] || fail "创建 Release 失败（HTTP $HTTP）"
RID=$(python3 -c "import json;d=json.load(open('$OUT_DIR/release-create.json'));print(d['id'])")
RELEASE_URL=$(python3 -c "import json;print(json.load(open('$OUT_DIR/release-create.json'))['html_url'])")
echo "release id: $RID"
echo "release: $RELEASE_URL"

echo "=== 5) 上传资产 ==="
ASSET_NAME=$(basename "$ZIP")
HTTP=$(curl --http1.1 -sS -o "$OUT_DIR/asset.json" -w "%{http_code}" \
  -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/zip" \
  --data-binary @"$ZIP" \
  "$UPLOAD_API/releases/$RID/assets?name=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$ASSET_NAME")")
[ "$HTTP" = "201" ] || fail "上传资产失败（HTTP $HTTP）"
python3 - "$OUT_DIR/asset.json" "$ZIP_SIZE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
size=int(sys.argv[2])
if int(d.get("size",-1)) != size:
    raise SystemExit(f"上传后大小不一致: 远端 {d.get('size')} / 本地 {size}")
print("asset:", d["name"], d["size"], d["browser_download_url"])
PY

if [ -n "${RELEASE_ASSETS_DIR:-}" ]; then
  [ -d "$RELEASE_ASSETS_DIR" ] || fail "RELEASE_ASSETS_DIR 不存在: $RELEASE_ASSETS_DIR"
  echo "=== 6) 上传额外资产 ==="
  GITHUB_TOKEN="$TOKEN" REPO="$REPO" bash "$REPO_ROOT/scripts/ci/upload-release-assets.sh" "$RID" "$RELEASE_ASSETS_DIR"
fi

echo "=== 完成：$RELEASE_URL ==="
