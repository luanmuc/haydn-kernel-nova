# haydn-kernel-nova

> **本仓库只维护 SukiSU-Nova builtin 线（Nova 线）。**
>
> BakaSU 稳定线在另一个独立仓库：
> https://github.com/luanmuc/android_kernel_xiaomi_sm8350_miyume
>
> 两条线不要混刷；Nova 线使用 `com.sukisu.nova` 管理器。

## 当前状态（2026-11-26）

### Android 14 FCM6 修复候选

- 构建提交：`27a492b20c1e9c2b3944dbd9255a4191eb8bfe41`
- 分支：`haydn/nova-fcm6`
- 云端 run：`45776535127`（success）
- Release：https://github.com/luanmuc/haydn-kernel-nova/releases/tag/haydn-27a492b20-fcm6-2026-11-26
- 状态：构建、FCM6 配置比对、AVB 校验通过；**弹窗/触摸/KSU 真机待验证，不是正式版**

本版从 Android 14 当前主线 `0ce563620` 出发，按设备实际导出的 `compatibility_matrix.6.xml` 一次性补齐 FCM6 缺失的 8 项内核配置：

- `CONFIG_ARM64_SW_TTBR0_PAN=y`
- `CONFIG_CFI_CLANG=y`
- `CONFIG_SHADOW_CALL_STACK=y`
- `CONFIG_HAVE_MOVE_PMD=y`
- `CONFIG_HAVE_MOVE_PUD=y`
- `CONFIG_CRYPTO_CHACHA20POLY1305=y`
- `CONFIG_CRYPTO_XCBC=y`
- `CONFIG_XFRM_MIGRATE=y`

快速临时启动：

```bash
adb reboot bootloader
fastboot boot Nova-haydn-patched-clean-boot-27a492b20-fcm6.img
```

`fastboot boot` 不改 boot 分区；clean boot 以 `0ce` clean boot 为底，仅替换 kernel，KSU ramdisk 沿用当前可工作的那套。

### Android 14 FCM6 弹窗回滚基线（0ce563620）

- `0ce563620`：`haydn/nova-builtin-new`
- Release：https://github.com/luanmuc/haydn-kernel-nova/releases/tag/haydn-0ce563620-official-2026-11-26
- 状态：SukiSU 可工作的稳定基线；当前 Android 14 / FCM6，仍缺 8 项配置，仍会有“您的设备内部出现了问题”弹窗，保留用于回滚和对照

## 版本线

- 构建分支：`haydn/nova-fcm6`（FCM6 修复候选）
- 主线分支：`haydn/nova-builtin-new`
- 默认文档分支：`haydn/nova`
- KSU：SukiSU-Nova `builtin`，固定 `5a3ec414`
- SUSFS：`v2.4.0`（GKI 5.10 核心移植到 5.4）
- 管理器：`com.sukisu.nova`
- 适用设备：Redmi K40 Pro / Pro+（haydn）

## 内核与编译

- 内核版本：5.4.302
- 默认配置：Clang 18.1.8 & LLD 18.1.8
- Haydn 使用 `arch/arm64/configs/haydn_defconfig`
- 编译：`bash build_device.sh haydn`

## 注意

- 不要刷 BakaSU 线的包，不要与 BakaSU 管理器混装。
- FCM6 修复候选尚未真机验证；验证前请保留 `0ce` clean boot 作为回滚底包。
