#!/usr/bin/env bash
# 便捷入口：实际逻辑在 check-upstreams.py。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/check-upstreams.py" "$@"
