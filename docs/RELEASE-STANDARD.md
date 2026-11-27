# 正式 Release 资产标准

适用于 `haydn/nova-builtin-new` 的每一次正式发布。**只发 AnyKernel3 不合格。**

## 必发资产

| 资产 | 用途 |
|---|---|
| `HoshinoNeko_haydn_<sha>_Any3Kernel.zip` | TWRP 永久刷入，只替换 kernel，保留当前 ramdisk/TWRP |
| `Nova-haydn-patched-clean-boot-<sha>-official.img` | clean ramdisk；`fastboot boot` 临时启动，也可 `fastboot flash boot` 永久刷入 |
| `Nova-haydn-patched-stock-boot-<sha>-official.img` | 原 stock ramdisk（含历史 Magisk/TWRP）；原 ramdisk 备选，可能覆盖 TWRP |
| `Image-<sha>-official` | 原始内核 Image；不是 boot image，不能直接刷 |
| `haydn-config-used-<sha>.txt` | 云端实际 config |
| `build-<sha>.log` | 构建日志 |
| `RELEASE-<sha>.md` | Release 说明存档 |
| `SHA256SUMS` | 上述资产的 sha256 |

## boot 镜像要求

- 以 `0ce563620` 的 clean boot / stock boot 为 ramdisk 底包；只替换 kernel。
- 如果新 Image 与原底包 kernel 大小不同，按 boot v3 布局重组：4K header + kernel + ramdisk，页对齐后重建 AVB footer。
- AVB 参数与既有 haydn boot 保持一致：
  - `Algorithm: NONE`
  - `Partition Name: boot`
  - `Salt: 4ce0907ef73ae9cceb8607c9681846e43c96d8c2fa20b92b9a1ea3c4d02d71be`
  - props：原 boot fingerprint、os_version 13、security_patch 2025-02-01
- 校验：
  1. 解出的 kernel SHA256 等于本次 `Image`。
  2. 解出的 ramdisk 与底包 ramdisk 完全一致。
  3. `avbtool info_image` 显示 `Algorithm: NONE` 且 digest 已更新。
  4. `avbtool verify_image` 通过；该工具按文件名找 `boot.img`，校验时复制成 `boot.img`。
  5. 上传后重新下载，核对远端大小与 SHA256。

## 发布脚本

正式发布时把 AK3 以外的资产放进同一个目录，并在创建 Release 时传入：

```bash
RELEASE_ASSETS_DIR=/path/to/release-assets \
  bash repo/scripts/ci/release.sh <tag> "<标题>" /path/to/RELEASE.md
```

`release.sh` 会先上传 AnyKernel3，再调用 `scripts/ci/upload-release-assets.sh` 上传目录内其余文件；已存在的同名资产会跳过，不会覆盖。

## 刷入方式说明

- 临时：`fastboot boot ...clean-boot...img`，不写 boot 分区。
- 永久（推荐）：TWRP 刷 AnyKernel3，保留当前 ramdisk。
- 永久（PC）：`fastboot flash boot` clean boot 或 stock boot；会替换当前 boot ramdisk，先备份。
- stock boot 含历史 Magisk/TWRP，可能与 SukiSU 冲突，只作为原 ramdisk 备选，不作为默认推荐。
