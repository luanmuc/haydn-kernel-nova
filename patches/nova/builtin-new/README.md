# builtin-new 线的补丁目录

`builtin-new` 已内置 SUSFS nofault 兼容和 `CMD_SUSFS_SET_SUS_PATH_UID_FILTER` 派发，
旧 `patches/nova/5.4` 的两支补丁不再适用于本线。

本线唯一的内核树改动是 `kernel/sys.c` 的 `ksu_handle_setresuid()` inline hook，
已直接提交在 `haydn/nova-builtin-new` 分支上；CI 不需要再额外打补丁。
