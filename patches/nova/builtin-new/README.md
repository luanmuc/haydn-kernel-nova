# builtin-new 线下游补丁台账

本目录不是一次性补丁堆放处，而是 `haydn/nova-builtin-new` 的长期下游补丁台账。

## 目录约定

```text
series                         # 按顺序生效的 active patch 列表
0001-ksu-inline-safe-mode.patch
cases/0001-ksu-inline-safe-mode.md
templates/patch-case.md
UPSTREAM_AUDIT.yaml            # 当前固定子模块 commit 与审计结论
```

规则：

- 每个 `.patch` 必须有一份同名 `cases/*.md`，记录现象、根因、验证和退役条件。
- 只有 `series` 里的补丁会被构建应用；顺序以 `series` 为准。
- `UPSTREAM_AUDIT.yaml` 的 `audited_submodule_commit` 必须等于构建时 `KernelSU` 子模块 HEAD，否则脚本直接失败。
- 补丁退役时从 `series` 移除并删除 `.patch`，但 `cases/*.md` 保留，状态改为 `retired`。
- 不直接修改 `KernelSU` 子模块工作区；所有改动通过 `patches/` 下的 patch 进入构建。

## 应用方式

```bash
./scripts/apply-nova-patches.sh --check   # 只检查审计和补丁可用性，不落盘
./scripts/apply-nova-patches.sh           # 构建前实际应用
```

脚本行为是严格的：

1. 子模块 commit 与 `UPSTREAM_AUDIT.yaml` 不一致 → 失败，强制先审计。
2. `series` 中的 patch 不存在、缺 case 文档或没有审计条目 → 失败。
3. 目录里存在 `.patch` 但没写进 `series`，或 `series` 出现重复项 → 失败。
4. patch 已应用 → 继续。
5. patch 冲突或未应用但 `apply --check` 失败 → 失败，不再静默跳过。

## 新增一个自己修的 bug

1. 按 `templates/patch-case.md` 新建 `cases/NNNN-xxxx.md`。
2. 生成 `NNNN-xxxx.patch`，文件名与 case 同名。
3. 把 patch 文件名加入 `series`，保持顺序。
4. 更新 `UPSTREAM_AUDIT.yaml`：当前子模块 commit、状态、观察路径、退役条件。
5. 本地 `--check` 通过后，再走云端编译和真机验证。

## 追上游更新

每次变更 `KernelSU` 子模块 commit：

1. 先看 `UPSTREAM_AUDIT.yaml` 中各 active patch 的 `watch_paths`。
2. 检查上游是否出现等价修复，不要求与我们的 patch 逐字一致。
3. 如果上游已修：把对应 case 标记 `upstream-fixed`，从 `series` 移除 patch，删除 `.patch`，保留 case 历史。
4. 如果上游没修：更新 `audited_submodule_commit` 和审计结论，继续带 patch。
5. 编译和真机回归后再提交。

旧 `patches/nova/5.4/` 的两支补丁已标记为 `OBSOLETE`，不得回退使用。
