# builtin-new 线的补丁目录

`builtin-new` 已内置 SUSFS v2.4 核心、5.4 适配、SUSFS nofault 兼容和
`CMD_SUSFS_SET_SUS_PATH_UID_FILTER` 派发。

本线当前没有额外 `.patch` 文件；唯一的内核树改动是 `kernel/sys.c` 的
`ksu_handle_setresuid()` inline hook，已直接提交在
`haydn/nova-builtin-new` 分支上，CI 不需要再额外打补丁。

旧 `patches/nova/5.4/` 的两支补丁已标记为 `OBSOLETE`，不得回退使用。
