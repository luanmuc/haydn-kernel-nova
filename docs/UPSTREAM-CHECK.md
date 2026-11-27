# 上游巡检

脚本：`scripts/ci/check-upstreams.sh`

实际逻辑：`scripts/ci/check-upstreams.py`

CI：`.github/workflows/check-upstreams.yml`

## 检查什么

三个上游：

| 上游 | 仓库 / 分支 |
|---|---|
| MiYume 内核 | `MiYume0721/android_kernel_xiaomi_sm8350_miyume` / `main` |
| SukiSU-Nova | `SukiSU-Nova/SukiSU-Nova` / `builtin-new` |
| SUSFS | `gitlab.com/simonpunk/susfs4ksu` / `gki-android14-5.15` |

脚本会做：

- 本地 pin 自检：主线 HEAD（pin 可以落后于当前 HEAD，但必须在当前历史中）、`KernelSU` 子模块 commit、`UPSTREAM_AUDIT.yaml`、SUSFS baseline 文件、baseline tag、内核底包 pin 祖先关系。
- 远端检查：三个目标分支 HEAD 与 pin 对比，判断是否前进、落后、分叉。
- 影响面摘要：列出新增 commit 和改动文件，按 haydn/KSU/SUSFS 相关路径标记“可能影响”。
- 管理器检查：SukiSU-Nova 最新 Release、arm64-v8a APK 文件名和 SHA256 是否与 pin 一致（需要 `GITHUB_TOKEN`）。

## 运行

```bash
bash scripts/ci/check-upstreams.sh
bash scripts/ci/check-upstreams.sh --format markdown
bash scripts/ci/check-upstreams.sh --format json
bash scripts/ci/check-upstreams.sh --offline
bash scripts/ci/check-upstreams.sh --fail-on-update
```

默认只报告，退出码 0；`--fail-on-update` 在有更新或本地 pin 失败时返回 2。网络/命令错误返回 1。

## CI

`.github/workflows/check-upstreams.yml` 每周一 09:00（Asia/Shanghai）跑一次，也可手动 `workflow_dispatch`。默认只把报告写进 Step Summary；手动触发时可勾选 `fail_on_update`。

脚本只读，不自动 fetch/merge/rebase，不自动改 `maintenance/ksu-pins.json`，也不自动发 Release。
