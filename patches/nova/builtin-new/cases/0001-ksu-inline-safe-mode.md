# 0001 · 开机完成后连按音量键误进安全模式

- 状态：active
- 创建日期：2026-11-27
- 目标：`KernelSU` 子模块（SukiSU-Nova `builtin-new`）
- 补丁文件：`0001-ksu-inline-safe-mode.patch`
- Patch SHA256：`f192bc02173bfe93a2e439f25a6ffaf974cff9d274a2d63b6a89680b1932b791`
- 当前固定 commit：`5a3ec4145059ed2c4f22c70a16a28a616e104c33`

## 现象

系统正常开机并进入桌面后，再连续按音量键三次，SukiSU Nova 管理器会显示“安全模式”。重启后该状态消失。

这不是开机早期真正的安全模式：已经加载的 root、模块和 SUSFS 隐藏仍然正常；但管理器会把 `safe_mode_flag` 当成真实状态，隐藏模块安装入口，ZIP 导入和 AI 模块安装被拦截，`ksud` 的部分模块脚本阶段也会被跳过。

## 复现条件

1. 正常开机，等待进入系统并完成 `post-fs-data`。
2. 在桌面连续按音量下键三次。
3. 打开 SukiSU Nova 管理器，出现“安全模式”标记。
4. 重启后标记消失，再次重复仍可触发。

关键点：触发发生在开机完成之后，而不是开机早期的音量键窗口。

## 影响范围

- root 本身不受影响。
- 已加载模块不会被晚到的标志卸载。
- SUSFS 隐藏不受影响。
- 管理器会隐藏模块安装按钮，并拒绝 ZIP 导入。
- `ksud` 的 `service` / `boot-completed` 阶段可能因 `is_safe_mode()` 跳过模块脚本。
- `ksud hot_install` 会拒绝安装。
- 因此这不是纯 UI 问题，需要修。

## 根因

调用链：

```text
drivers/input/input.c
  -> ksu_handle_input_handle_event(&type, &code, &value)
     -> vol_down_cnt++ / vol_up_cnt++
        -> 达到 3 次后 safe_mode_flag = true
```

具体问题：

1. `drivers/input/input.c:386` 在任何输入事件中都会无条件调用 `ksu_handle_input_handle_event()`，没有检查 inline hook 是否已经停止。
2. `KernelSU/kernel/runtime/ksud_integration.c:632` 的 handler 只做计数和置位，完全不检查 `ksu_input_hook_active()`。
3. `ksu_stop_input_hook_runtime()` 在 `ksud_integration.c:795` 会设置 `ksu_input_hook = false`，并在 `CONFIG_KSU_SUSFS` 下关闭 `ksu_is_input_hook_enabled` static key；但 producer 仍然在调用 handler。
4. `ksu_is_safe_mode()` 在 `ksud_integration.c:573` 是“先 stop，再读 `safe_mode_flag`”；`already_checked` 只在返回 true 时置位，第一次返回 false 不会锁存“正常状态”，后续 handler 仍可把 flag 翻成 true。
5. `on_post_fs_data()` 在 `KernelSU/kernel/runtime/boot_event.c:16` 会调用 `ksu_stop_input_hook_runtime()`，所以正常启动路径本来应该在 `post-fs-data` 后停止采样；但 inline handler 没有 guard，导致“停止”只停了标志，没有停实际采样。

结论：这是 `CONFIG_KSU_SUSFS_INLINE_HOOK` 后端新增后形成的回归。此前的非 inline 修复没有迁移到 inline 路径。

## 补丁思路

在 `ksu_handle_input_handle_event()` 开头增加：

```c
if (!READ_ONCE(ksu_input_hook) || !ksu_input_hook_active())
    return 0;
```

`ksu_stop_input_hook_runtime()` 先设置 `ksu_input_hook = false`，再关闭 static key。只检查 static key 会留下一个很短的窗口：bool 已经为 false，但 key 还没关闭，此时仍可能采样。同时检查两者后，停止动作一开始就会挡住 handler；static key 则覆盖其他可能单独关闭 key 的路径。

这样 `ksu_stop_input_hook_runtime()` 执行后，晚到的音量键不会修改 `safe_mode_flag`。开机早期的三次音量键仍然有效，因为那时 hook 仍处于 active 状态。

没有选择在 `ksu_is_safe_mode()` 里锁存 false，因为那可能过早关闭真正早期安全模式窗口；也没有选择改 `input.c`，因为当前修复点位于 `KernelSU` 子模块，补丁边界更小，便于后续退役。

## 验证

当前状态：

- `git apply --check`：已通过。
- 本地台账门禁：`--check` 通过；实际 apply、重复执行识别“已应用”、回退均通过。
- 编译验证：云端 run `45918531589` success；build log 0 error / 15 条原有 warning。
- 真机验证：2026-11-27 通过。刷入 `07e07dff3` 后，开机完成再连按音量下键三次不进入安全模式；重启后在开机早期连按三次音量键仍能进入真正的安全模式；KSU 工作中，9 个模块，内核版本 `5.4.302-HoshinoNeko-nova-g07e07dff`。

已验证步骤：

1. 云端构建通过，确认 `CONFIG_KSU=y`、`CONFIG_KSU_SUSFS=y`、`CONFIG_KSU_SUSFS_INLINE_HOOK=y`。
2. 刷入后正常开机，等待进入桌面。
3. 连按音量下键三次，管理器未出现安全模式。
4. 重启，在开机早期连按三次音量键，仍能进入真正的安全模式。
5. root、模块加载和 KSU 状态正常。
6. 反向验证未重新构建无补丁镜像；原 `27a492b20` 已实际复现晚到三击误报。

## 上游观察

当前固定的 `KernelSU` commit 是 `5a3ec4145059ed2c4f22c70a16a28a616e104c33`，`ksu_handle_input_handle_event()` 仍没有 hook active 保护。

每次追 `builtin-new` 更新时检查：

- `KernelSU/kernel/runtime/ksud_integration.c` 的 `ksu_handle_input_handle_event()` 是否新增 `ksu_input_hook_active()` 或等价判断。
- `KernelSU/kernel/runtime/ksud.c` 的停止路径是否改成真正阻止 producer 采样。
- 新 commit 是否已进入本仓库固定的子模块。

不向上游提交 PR；只做本地审计和被动观察。

## 退役条件

上游 `builtin-new` 满足以下任一条件，并进入本仓库固定的 `KernelSU` commit 后，才能退役：

- `ksu_handle_input_handle_event()` 内有 `ksu_input_hook_active()` 或等价保护；
- 或 `ksu_stop_input_hook_runtime()` 之后 producer 不再调用 handler；
- 且真机验证“开机后三击不误报、开机早期三击仍可进安全模式”。

退役动作：

1. 从 `series` 移除 `0001-ksu-inline-safe-mode.patch`；
2. 删除 patch 文件；
3. 本 case 标记 `retired`，保留历史，不删除；
4. 更新 `UPSTREAM_AUDIT.yaml` 的固定 commit 和审计结论；
5. 重新编译和真机回归。

## 变更历史

- 2026-11-27：创建补丁与案卷；`git apply --check` 通过。
- 2026-11-27：云端 run `45918531589` 编译通过；真机验证通过（晚到三击不误报、开机早期三击仍可进安全模式）。
