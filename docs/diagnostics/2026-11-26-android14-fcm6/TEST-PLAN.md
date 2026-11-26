# haydn Nova 触摸/弹窗矩阵测试单（run 45719834851）

- 基线：`469e7e420`（能启动、弹窗消失、KSU 正常，锁屏触摸失效）
- 共同点：`CFI_CLANG` / `SHADOW_CALL_STACK` / `ARM64_SW_TTBR0_PAN` / `CFI_PERMISSIVE` 这组硬化开关参与矩阵；KSU/SUSFS 保留
- 所有 clean boot 都是 201,326,592 bytes，`fastboot boot` 临时启动；内核已核对与各自 `Image` 的 SHA256 一致

## 建议测试顺序

| 顺序 | 变体 | 只改了什么 | 预期弹窗 | 触摸预期 | 目的 |
|---|---|---|---|---|---|
| 1 | `scs-vmap-off` | 只关 `SHADOW_CALL_STACK_VMAP` | 应消失 | 若恢复，说明是 SCS VMAP 导致触摸坏 | 最小变量，优先试 |
| 2 | `cfi-shadow-off` | 只关 `CFI_CLANG_SHADOW` | 应消失 | 若恢复，说明是 CFI shadow 导致触摸坏 | 最小变量，优先试 |
| 3 | `strict-pauth` | 只关 `CFI_PERMISSIVE`（CFI 变严格） | 应消失 | 可能仍失效；也可能黑屏 | 对照：确认 permissive 是否是启动必需 |
| 4 | `sw-off` | 只关 `ARM64_SW_TTBR0_PAN` | 可能回来 | 若恢复，说明是 SW PAN 导致触摸坏 | 触摸定位 |
| 5 | `scs-off` | 关 `SHADOW_CALL_STACK` + `SHADOW_CALL_STACK_VMAP` | 可能回来 | 若恢复，说明是 SCS 导致触摸坏 | 触摸定位 |
| 6 | `cfi-off` | 关 `CFI_CLANG` + `CFI_CLANG_SHADOW` + `CFI_PERMISSIVE` | 可能回来 | 若恢复，说明是 CFI 导致触摸坏 | 触摸定位 |
| 7 | `nopauth` | 关 `ARM64_PTR_AUTH`，其余不变 | 应消失 | 按 Kconfig 预计仍失效 | 排除 PAuth 是触摸根因 |

## 判定

- 若 1 或 2 能“弹窗消失 + 触摸正常”：直接锁定最小关闭项，后面只需把该项做成正式配置。
- 若 1/2 触摸仍失效，但 4/5/6 中某一项触摸恢复：说明触摸问题是该硬化项导致，需要做驱动/调用约定级兼容修复；弹窗则按上游已知提示处理。
- 若 3 黑屏：属预期对照结果，不说明镜像坏；它证明 `CFI_PERMISSIVE` 是这组配置能启动的必要条件。
- 若 7 触摸仍失效：PAuth 与触摸无关，不再在 PAuth 上花时间。

## 文件

每个变体目录里：

- `Nova-haydn-patched-clean-boot-<variant>-c1dc25c.img`：`fastboot boot` 用
- `Image-<variant>-c1dc25c`：裸内核
- `HoshinoNeko_haydn_c1dc25ce1_<variant>_Any3Kernel.zip`：TWRP/AnyKernel 用
- `SHA256SUMS.txt`：本目录校验和
