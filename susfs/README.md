# SUSFS v2.4.0 基线（Linux 5.4 / haydn）

> **本目录不参与编译**，只用于长期维护：记录来源、校验本地集成漂移、保存可复现基线。

## 上游锚点

| 项 | 值 |
|---|---|
| 上游仓库 | `https://gitlab.com/simonpunk/susfs4ksu`（作者 `simonpunk`） |
| 上游分支 | `gki-android14-5.15` |
| 版本号提交 | `dccbd671327887a81b74c6b96446e7b9fca85e4b`（`Bump version to 2.4.0`，2026-11-08） |
| **不可变功能锚点** | `1e55ec9a51a30cabd70fb403a8853050e355a9f3`（`kernel & ksu_susfs: Add sus_path_uid_filter feature`，2026-11-15） |
| 审计时分支头 | `a293ab199ff84b7482d57ece06b4199411cd5c01`（2026-11-15，仅记录观察值，不作为字节锁） |
| 内核版本 | 5.4.302 / haydn |
| 本地版本 | `include/linux/susfs.h` → `v2.4.0` |

说明：上游仓库当前没有可直接使用的 `v2.4.0` tag；本次以 `1e55ec9` 作为**不可变 commit 锚点**。`a293ab1` 是审计时分支头，后续上游可能继续移动；不能把分支头当成固定 pin。

## 本地 port

- 核心 port：`33a596ca4`（`Nova: port SUSFS v2.4 core and adapt 5.4 hooks`）
- 5.4 fsnotify 适配：`cc0160a65`
- 5.4 `filename_lookup` 声明：`c1a9d1548`
- devpts guard 调整：`ee076cc81`
- UID filter 接线：`4e8e4cb2e`（旧线）及 `builtin-new` 分支内置
- 当前 HEAD：`aa4e8e2e2d517cbacf44cb41143a0205a5475b53`
- 当前 KSU 子模块：`5a3ec4145059ed2c4f22c70a16a28a616e104c33`（`builtin-new`）

## 基线文件（10 个）

| 文件 | 作用 |
|---|---|
| `fs/susfs.c` | SUSFS 主体实现 |
| `include/linux/susfs.h` | 对外 API / 版本号 |
| `include/linux/susfs_def.h` | 常量、结构体、flag |
| `fs/notify/fdinfo.c` | fdinfo 伪装 |
| `fs/proc/fd.c` | fd 重验证 |
| `fs/proc/task_mmu.c` | maps 伪装（SRCU） |
| `fs/proc_namespace.c` | mountinfo/mounts 伪装 |
| `fs/stat.c` | stat/statx kstat 伪装 |
| `fs/statfs.c` | statfs 伪装 |
| `fs/super.c` | KSU 匿名块设备隔离 |

编译入口：`fs/Makefile` 的 `obj-$(CONFIG_KSU_SUSFS) += susfs.o`；所有调用点均有 `CONFIG_KSU_SUSFS` guard。

## 基线的语义（重要）

`susfs/baseline.sha256` 是**本地 5.4 集成指纹**，不是上游 5.10 文件的逐字节副本。原因：

- 上游核心是 GKI 5.10/6.x 代码，5.4 需要 `filename_lookup`、`fsnotify handle_event`、`strncpy_from_user_nofault` 等适配。
- v2.3 → v2.4 升级会改变 `fs/stat.c`、`fs/susfs.c`、`include/linux/susfs_def.h`、`include/linux/susfs.h` 四个核心文件。
- 因此 baseline 的作用是：**锁定当前 5.4 集成后的文件指纹，发现后续未记录的本地漂移**；它不能证明与上游文件的字节一致性。

`check-baseline.sh` 输出全部 `OK` 只代表：

1. 10 个集成文件与本地 v2.4 基线一致；
2. 当前提交没有在基线之外偷偷改 SUSFS 核心文件。

它不代表真机 SUSFS 行为通过。

## 目录说明

```
susfs/
├── README.md                 # 本文件
├── baseline.sha256           # 10 个文件的本地集成指纹
├── patches/
│   └── 0001-v2.1.0-to-v2.3.0.patch  # 历史补丁，不用于当前线
└── scripts/
    └── check-baseline.sh     # 校验本地集成是否漂移
```

`patches/0001-v2.1.0-to-v2.3.0.patch` 是 v2.1→v2.3 的历史材料，不再适用于 v2.4 / `builtin-new`；不要把它当作当前补丁。

## 校验

```bash
bash susfs/scripts/check-baseline.sh
```

输出全部 `OK` 表示本地集成与 v2.4 基线一致；任何 `FAILED` 都必须先判断是“有意升级”还是“误改”，不能直接重新生成 baseline 掩盖漂移。

## 更新基线的规则

1. 只在 `haydn/test` 上做 SUSFS 变更。
2. 通过 `SUSFS=y` / `SUSFS=n` 双构建 + 真机验证后，才合入稳定线。
3. 合并后重新生成 `baseline.sha256`，打本地 tag `susfs-baseline-v2.4.0`。
4. 不追新功能，只接 KSU 新 API、实测 bug、稳定性/安全修复（详见 `PORTING.md`）。
5. 每次改 baseline 必须在提交说明中记录：改了什么、为什么、对应上游 commit；禁止只更新哈希不写原因。
