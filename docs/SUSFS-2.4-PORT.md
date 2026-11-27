# Nova SUSFS v2.4.0 5.4 移植记录

## 结论

- 目标线：SukiSU-Nova `builtin-new`，commit `5a3ec4145059ed2c4f22c70a16a28a616e104c33`
- 当前正式版：`8c4f9557d3fe58469f2b2b1c02a06d8c91babbf7`，tag `haydn-8c4f9557d-official-2026-11-27`
- SUSFS：`v2.4.0`；上游锚点 `1e55ec9a51a30cabd70fb403a8853050e355a9f3`（GitLab `simonpunk/susfs4ksu`，`gki-android14-5.15`）
- 版本号提交：`dccbd671327887a81b74c6b96446e7b9fca85e4b`
- 5.4 适配：`33a596ca4`、`cc0160a65`、`c1a9d1548`、`ee076cc81`
- 当前完整构建：run `46013425604`，`Success`（提交 `8c4f9557d`）
- 产物：`Image-8c4f9557d-official`，SHA256 `09c96212a988c6f68836321798d5b92fdaeb7791acc64327b7ec7c54c6c71da2`
- 状态：**核心已随 07e 正式版真机验证；8c 只关闭 SUSFS 日志，Android 14 真机启动通过**

## 生效配置

- `CONFIG_KSU=y`
- `CONFIG_KSU_SUSFS=y`
- `CONFIG_KSU_SUSFS_SUS_PATH=y`
- `CONFIG_KSU_SUSFS_SUS_MOUNT=y`
- `CONFIG_KSU_SUSFS_SUS_KSTAT=y`
- `CONFIG_KSU_SUSFS_OPEN_REDIRECT=y`
- `CONFIG_KSU_SUSFS_SUS_MAP=y`
- `CONFIG_KSU_SUSFS_ENABLE_LOG=n`（8c 正式版关闭；07e 为 y）
- `CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y`
- `CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y`
- `CONFIG_LOCALVERSION="-HoshinoNeko-nova"`

## 5.4 适配点

- `fs/open.c` / `fs/stat.c`：改为 `getname_flags()` + `filename_lookup()`，钩子传递 `struct filename **`；5.4 没有 `filename_lookup()` 头声明，已显式声明。
- `fs/exec.c`：保留 pre-exec `ksu_handle_execveat()`；对 SUSFS 分支用返回值判定 su session，成功 exec 后调用 `ksu_handle_post_execveat_sucompat()`。
- `fs/readdir.c`：2.4 核心没有 `susfs_get_data_path()`，在 `fs/susfs.c` 补回 5.4 兼容实现。
- `fs/susfs.c`：2.4 的 fsnotify 回调使用 5.10 的 `handle_inode_event`；5.4 的 `fsnotify_ops` 只有 `handle_event`，已按 5.4 签名分支实现。
- `fs/devpts/inode.c`：旧的非 SUSFS `ksu_handle_devpts` 钩子只在 `!CONFIG_KSU_SUSFS` 时保留；SUSFS 分支没有该符号。
- `KernelSU/kernel/sulog/event.c`：旧 `patches/nova/5.4/0001-sulog-nofault.patch` 是历史兼容材料，`builtin-new` 线不再由 CI 应用；当前以子模块 `5a3ec414` 的实际源码为准。

## 补丁策略

- `builtin-new` 已内置 v2.4 核心、UID filter 派发和 5.4 适配；`patches/nova/builtin-new/` 当前没有 `.patch` 文件。
- `patches/nova/5.4/` 是旧 `builtin` 线材料，已加 `OBSOLETE.md`，**不得再套到 `builtin-new`**。
- `scripts/apply-nova-patches.sh` 只读取 `patches/nova/builtin-new/`；该目录没有补丁时直接跳过，不再回退到 `patches/nova/5.4`。

## 命令层审计

- `KernelSU/kernel/supercall/dispatch.c` 的 `CMD_SUSFS_*` 派发已与 `susfs_def.h` 对齐检查。
- `CMD_SUSFS_SET_SUS_PATH_UID_FILTER` -> `susfs_set_sus_path_uid_filter()` 已在 `builtin-new` 内核树中接线。
- `CMD_SUSFS_SET_PRIORITY_UID_FILTER`、`CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING`、`CMD_SUSFS_SHOW_ENABLED_FEATURES`、`CMD_SUSFS_SHOW_VERSION` / `SHOW_VARIANT` 已接线。
- 仍保留的未派发命令均为 2.4 头里的 deprecated 命令（`ADD_SUS_MOUNT`、`ADD_TRY_UMOUNT`、`SUS_SU`、`IS_SUS_SU_READY`、旧 root path 命令等），不应当作新功能使用。

## 验证状态 / 风险

- 已随 `07e07dff3` 正式版真机运行：root 授权、模块加载、SUSFS 功能页 9/9 正常；13 个超级用户、9 个模块。`8c4f9557d` 仅关闭 SUSFS 日志，Android 14 真机启动通过，核心功能与 07e 一致。
- `ksu_handle_post_execveat_sucompat()` 的 su session 判定依赖 `ksu_handle_execveat()` 返回 0；正式版已验证 su fd / 管理器授权链可用。
- 5.4 `fsnotify` 的 `handle_event` 与 5.10 `handle_inode_event` 语义接近但不完全等价；常规路径正常，单项隐藏行为按需回归。
- `CONFIG_KSU_SUSFS_SUS_KSTAT` 的 `susfs_get_non_sus_mnt_id_from_mnt()` 依赖 `CONFIG_KSU_SUSFS_SUS_MOUNT`；当前默认开启，若后续裁掉 SUS_MOUNT 需要补依赖或空实现。
- 本文件保留移植审查点；正式版结论以当前 Release 和真机验证记录为准。
