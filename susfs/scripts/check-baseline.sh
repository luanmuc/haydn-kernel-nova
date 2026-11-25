#!/usr/bin/env bash
# 校验工作树中的 SUSFS 集成文件是否仍等于本地 v2.4.0 基线（不是上游字节锁）
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

if [ ! -f susfs/baseline.sha256 ]; then
  echo "缺少 susfs/baseline.sha256" >&2
  exit 1
fi

echo "=== SUSFS baseline check ($(pwd)) ==="
if sha256sum -c susfs/baseline.sha256; then
  echo "=== 结果：全部一致 ==="
else
  echo "=== 结果：存在漂移，请确认是有意升级还是误改 ===" >&2
  exit 1
fi
