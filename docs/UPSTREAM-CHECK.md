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

`.github/workflows/check-upstreams.yml` 每天 09:00（Asia/Shanghai）跑一次，也可手动 `workflow_dispatch`。默认只把报告写进 Step Summary；手动触发时可勾选 `fail_on_update`。

通知策略：**只在有上游更新、本地 pin 失败、巡检错误或管理器不一致时通知**；全部正常时不打扰。通知顺序：

1. 配置仓库 secret `FEISHU_WEBHOOK_URL` 时，发飞书群机器人；如果机器人启用了签名校验，再配置 `FEISHU_WEBHOOK_SECRET`。
2. 没有飞书 webhook，或飞书发送失败时，自动在仓库创建/更新 `[上游巡检] 需要处理` Issue，并 @仓库 owner 兜底。

通知脚本：`scripts/ci/notify-upstreams.py`，可用 `--dry-run` 本地预览。

脚本只读，不自动 fetch/merge/rebase，不自动改 `maintenance/ksu-pins.json`，也不自动发 Release。
