# haydn-kernel-nova

Redmi K40 Pro / K40 Pro+（haydn）的 **SukiSU-Nova builtin** 内核线。仓库只保留一条主线：`haydn/nova-builtin-new`。

> BakaSU 稳定线在独立仓库：<https://github.com/luanmuc/haydn-kernel-bakasu>
> 两条线不要混刷；Nova 线管理器包名是 `com.sukisu.nova`。

## 当前正式版

| 项 | 值 |
|---|---|
| 内核 | `5.4.302-HoshinoNeko-nova-g07e07dff` |
| 提交 / tag | `07e07dff3` / `haydn-07e07dff3-official-2026-11-27` |
| KSU | SukiSU-Nova `builtin-new`，子模块 `5a3ec414`，内核显示 `30007-6` |
| SUSFS | `v2.4.0 (SUSFS Inline Hook)`，真机验证通过 |
| 管理器 | 上游 `v3.0.0`，`35000-6`，`com.sukisu.nova` |
| 设备 | Redmi K40 Pro / K40 Pro+（haydn），Android 14 |
| Release | [haydn-07e07dff3-official-2026-11-27](https://github.com/luanmuc/haydn-kernel-nova/releases/tag/haydn-07e07dff3-official-2026-11-27) |
| 状态 | 安全模式误报修复已真机双验证；13 个超级用户、9 个模块 |

本版修复了 inline input hook 在停止采样后仍累计音量键、导致开机完成后三击音量下键误进安全模式的问题；重启后早期三击仍能进入真正的安全模式。

## 发布资产

正式 Release 固定为 8 个资产：

- `HoshinoNeko_haydn_<sha>_Any3Kernel.zip`：TWRP 永久刷入，只替换 kernel，保留当前 ramdisk/TWRP。
- `Nova-haydn-patched-clean-boot-<sha>-official.img`：clean ramdisk，`fastboot boot` 临时启动，也可 `fastboot flash boot` 永久刷入。
- `SukiSU_Nova_v3.0.0_35000-arm64-v8a-release.apk`：上游配套管理器，arm64-v8a。
- `Image-<sha>-official`：原始内核 Image，**不是 boot image，不能直接刷**。
- `haydn-config-used-<sha>.txt`、`build-<sha>.log`、`RELEASE-<sha>.md`、`SHA256SUMS`：配置、日志、说明和校验和。

**不发布带 Magisk/TWRP 的 stock boot。** 需要刷 boot 分区时用 clean boot。

## 刷入

临时启动，不写 boot 分区：

```bash
adb reboot bootloader
fastboot boot Nova-haydn-patched-clean-boot-07e07dff3-official.img
```

永久刷入，推荐 TWRP 刷 `HoshinoNeko_haydn_07e07dff3_Any3Kernel.zip`，保留当前 ramdisk/TWRP。也可以从 PC 执行：

```bash
fastboot flash boot Nova-haydn-patched-clean-boot-07e07dff3-official.img
```

该命令会替换当前 boot ramdisk，执行前先备份。clean boot 已完成 kernel 段、ramdisk 和 AVB 校验，但 `fastboot boot` 未单独做真机验证；第一次使用建议先临时启动确认。

管理器直接安装 Release 里的上游 APK；已安装同包名旧版可覆盖安装。不要混用 BakaSU 管理器或本地旧 APK。

## 编译

```bash
bash build_device.sh haydn
```

- 内核版本：`5.4.302`
- 默认工具链：Clang 18.1.8 / LLD 18.1.8
- defconfig：`arch/arm64/configs/haydn_defconfig`

## 维护约定

- 只保留 `haydn/nova-builtin-new` 一条主线；不再保留 stable/test/feature 长期分支。
- 正式 tag 从主线 commit 打；Release 资产按 [`docs/RELEASE-STANDARD.md`](docs/RELEASE-STANDARD.md) 执行。
- 历史默认分支 `haydn/nova` 已并入主线并删除；历史 FCM6、CFI 试验分支已清理。
- KSU 线说明见 [`docs/KSU-LINE.md`](docs/KSU-LINE.md)，SUSFS 移植记录见 [`docs/SUSFS-2.4-PORT.md`](docs/SUSFS-2.4-PORT.md)，CI 日志规则见 [`docs/CI-LOG-POLICY.md`](docs/CI-LOG-POLICY.md)。
- 发布说明模板见 [`docs/RELEASE-TEMPLATE.md`](docs/RELEASE-TEMPLATE.md)。

## 禁止

- 不刷 BakaSU 线的包；不要与 BakaSU 管理器混装。
- 不使用本地旧管理器 APK；管理器必须取上游对应 Release 的 arm64-v8a 包。
- 不发布、不刷带历史 Magisk/TWRP 的 stock boot。
