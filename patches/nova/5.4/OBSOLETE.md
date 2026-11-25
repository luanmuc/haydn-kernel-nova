# OBSOLETE：旧 `builtin` 线 5.4 补丁

本目录的两支补丁：

- `0001-sulog-nofault.patch`
- `0002-susfs-uid-filter-dispatch.patch`

属于旧 `builtin` 线（`4bec532d` 时代）的历史材料。

当前线 `haydn/nova-builtin-new` 已内置对应的 v2.4 逻辑：

- SUSFS v2.4 核心与 5.4 适配
- `CMD_SUSFS_SET_SUS_PATH_UID_FILTER` 派发
- `strncpy_from_user_nofault` 的兼容处理

因此：

1. 不要在本线手工 `git apply` 这两支补丁；
2. 不要把本目录作为 `scripts/apply-nova-patches.sh` 的回退目录；
3. 需要追溯旧线行为时再读，不能把旧补丁结果当成当前树状态。
