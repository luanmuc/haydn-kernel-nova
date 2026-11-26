# Android 14 FCM6 弹窗定位与 7 个诊断包归档

日期：2026-11-26  
设备：Redmi K40 Pro+（haydn）  
当前系统：Android 14，指纹 `Redmi/haydnpro/haydn:14/UKQ1.231207.002/V816.0.15.0.UKKCNXM:user/release-keys`

## 结论

“您的设备内部出现了问题。请联系您的设备制造商了解详情。”不是第三方 App 弹窗，而是 `system_server` 的 `ActivityTaskManagerService.showSystemReadyErrorDialogsIfNeeded()`。

触发链：

1. `Build.isBuildConsistent()`
2. `VintfObject.verifyWithoutAvb()`
3. 返回非 0，显示字符串 `system_error_manufacturer`

参考：<http://www.shturl.cc/59bc79b5ee92c90c87d94033e5999395>

因此它是 **Android 14 FCM6 的 VINTF 一致性检查失败**，不是随机 bug，也不是靠清缓存、点确定能永久消除的。

## 当前 0ce 相对 FCM6 缺的 8 项

上传的 `reference/compatibility_matrix.6.xml` 根节点为 `compatibility-matrix version="7.0" type="framework" level="6"`，对应 Android 14。

| 缺失项 | 所属块 | 作用 |
|---|---|---|
| `CONFIG_ARM64_SW_TTBR0_PAN` | arm64 | 软件 PAN |
| `CONFIG_CFI_CLANG` | arm64 | Clang CFI |
| `CONFIG_SHADOW_CALL_STACK` | arm64 | 影子调用栈 |
| `CONFIG_HAVE_MOVE_PMD` | arm64 | PMD 级页表移动能力 |
| `CONFIG_HAVE_MOVE_PUD` | arm64 | PUD 级页表移动能力 |
| `CONFIG_CRYPTO_CHACHA20POLY1305` | 通用 5.4.86 | ChaCha20-Poly1305 |
| `CONFIG_CRYPTO_XCBC` | 通用 5.4.86 | XCBC |
| `CONFIG_XFRM_MIGRATE` | 通用 5.4.86 | XFRM 迁移 |

当前 config 对照文件：`configs/0ce-config.txt`、`reference/current-config.txt`。两者 SHA-256 相同：`45a6520a550552ff506c61aafe2bb5e8b4ed52b84d5338735f702d698756fded`。

## 为什么 7 个测试包在 Android 14 上作废

7 个包都是从 `469e7e420` 派生，只补了 FCM6 里的前 3 项（`ARM64_SW_TTBR0_PAN`、`CFI_CLANG`、`SHADOW_CALL_STACK`）。

`469` 本身对照 FCM6 仍缺 5 项：

- `CONFIG_HAVE_MOVE_PMD`
- `CONFIG_HAVE_MOVE_PUD`
- `CONFIG_CRYPTO_CHACHA20POLY1305`
- `CONFIG_CRYPTO_XCBC`
- `CONFIG_XFRM_MIGRATE`

所以：

- `01 scs-vmap-off`、`02 cfi-shadow-off`、`03 strict-pauth`、`07 no-PAuth` 保留 FCM5 三项，但还缺上述 5 项，Android 14 下仍过不了 FCM6；
- `04 sw-off`、`05 scs-off`、`06 cfi-off` 主动关掉 FCM6 必需项，更过不了。

这些包只适合作为 Android 13/FCM5 的触摸变量对照，不再作为 Android 14 的候选。

## 7 个 artifact 清单

完整机器可读清单见 `artifacts.tsv`。

| run | variant | artifact id | 结果 |
|---|---|---|---|
| 45719834851 | strict-pauth | 15073135256 | 已删除 |
| 45719834851 | scs-vmap-off | 15074145058 | 已删除 |
| 45719834851 | cfi-shadow-off | 15073272060 | 已删除 |
| 45719834851 | scs-off | 15072174936 | 已删除 |
| 45719834851 | cfi-off | 15073166231 | 已删除 |
| 45719834851 | sw-off | 15072541776 | 已删除 |
| 45665278740 | no-PAuth | 15048776679 | 已删除 |

云端临时分支 `haydn/nova-vintf-matrix` 已删除，分支 tip 为 `c1dc25ce10be2ba983a0a3f81a269f32982f6543`。

## 归档内容

- `TEST-PLAN.md`：原 7 包测试单，仅作历史记录，不再作为 Android 14 测试计划。
- `SHA256SUMS-ALL.txt`：7 个 clean boot 的原始校验和。
- `configs/`：0ce、469、no-PAuth 三份关键 config。
- `build-logs/`：7 个变体的构建日志。
- `reference/`：当前系统上传的 `compatibility_matrix.6.xml` 与 `current-config.txt`。
- `build-recipe/`：原矩阵 workflow 与 `apply-variant.py`，仅作复现参考，不参与当前主线构建。
- `artifacts.tsv`：7 个 Actions artifact 的 id、名称、大小。

49 MB 的 `boot.log` 未归档：其 `system` buffer 从 06:50 才开始，而本次开机是 01:21，早期 system_server 日志已被环形缓冲区覆盖；其中没有 VINTF 字样，不能作为“未失败”的证据，也没有长期保留价值。

## 清理记录

- 本地 `matrix-45719834851/`（约 1.9 GB）已删除。
- 本地 `Nova-haydn-7-test-2026-11-26.zip`（约 303 MB）已删除。
- 云端 `haydn/nova-vintf-matrix` 分支已删除。
- 云端 7 个测试 artifact 已删除（run `45719834851` 六个 + run `45665278740` 一个）。
- `0ce563620` 正式 Release、clean boot、AnyKernel、config 均保留，作为当前可用基线。

## 后续方向

下一版不要继续拿这 7 个包刷。应先做一个 **Android 14 FCM6 合规版**：

1. 在 469 基础上补上后 5 项；
2. `CONFIG_HAVE_MOVE_PMD` / `CONFIG_HAVE_MOVE_PUD` 若 defconfig 无法直接生效，需要在 arm64 Kconfig 中 select；
3. 保留 `CFI_PERMISSIVE=y`，避免严格 CFI 黑屏；
4. 先验证 8 项全补齐后弹窗是否消失，再在这个 FCM6 基线上做触摸单变量测试。
