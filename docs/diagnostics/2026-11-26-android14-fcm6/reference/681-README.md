# Nova haydn VINTF FCM5 修复构建（681c358a）

日期：2026-11-25

## 结论

弹窗根因是 FCM5 `compatibility_matrix.5.xml` 的 5.4.61 arm64 kernel 段要求以下配置，而 0ce 原配置缺失：

- `CONFIG_ARM64_SW_TTBR0_PAN=y`
- `CONFIG_CFI_CLANG=y`
- `CONFIG_SHADOW_CALL_STACK=y`

本构建已全部开启，arm64 FCM5 段静态比对 **0 个 mismatch**。

## 构建

| 项 | 值 |
|---|---|
| 分支 | `haydn/nova-vintf-fix` |
| 提交 | `681c358a42dd540d657af2902c7312ad2116bead` |
| 云端 run | `45641508472` |
| 结果 | Success |
| 构建耗时 | 28:40 |
| build log | 15 warnings / 0 error |
| Image | 53,160,448 bytes，SHA256 `6677de66432cc771829bfbad77592fa1ba4a852c4a721555405053150fd04e83` |
| 内核版本 | `5.4.302-HoshinoNeko-nova-g681c358a` |
| clean boot | 201,326,592 bytes，SHA256 `4065c6cef33be930a4de1cfb980068734bb44cbec4b83ce85d49e6fad185fe63` |
| AnyKernel | 26,541,550 bytes，SHA256 `b884b7f6809d19849e120e5bfba26f741a94e40e5580eb80f3769229899504c9` |

## Boot 校验

- clean boot 内 kernel SHA256 与 `Image-681c358a` 一致：`6677de...`
- ramdisk SHA256 与旧 clean ramdisk 一致：`29254f09...`
- AVB footer：`Algorithm NONE`，`Original image size 73,064,448`，`Image Size 73,064,448`
- `avbtool verify_image`：`Successfully verified footer and NONE vbmeta struct`
- `avbtool verify_image`：`Successfully verified sha256 hash ... for image of 73064448 bytes`

## 真机测试

先临时启动，不写分区：

```bash
fastboot boot Nova-haydn-patched-clean-boot-vintf-fix-681c358a.img
```

重点看：

1. 开机是否还出现“您的设备内部出现了问题。请联系您的设备制造商了解详情。”
2. SukiSU Nova 是否正常显示“工作中”
3. Wi-Fi / 蓝牙 / 相机 / 指纹 / 触摸 / 扬声器 / 通话 / 充电 / USB / UFS / 显示

如果 `fastboot boot` 被 bootloader 拒绝，不要改成 `fastboot flash boot`；先回原 boot。

回滚用官方纯净 boot：

```text
https://aka.doubaocdn.com/s/3mnVzh4olQ
SHA256 3253bb08df4ad272bb8d8574a55e15dba66bad8507c0959a7e39a43d48e35498
```

## 说明

- 本次只产出 clean boot 用于临时验证；未永久刷入，未装 TWRP。
- CFI/SCS 按官方配置开启，`CONFIG_CFI_PERMISSIVE` 未开；若 vendor `.ko` 触发 CFI，先记录，再单独编 permissive 对照。
- `CONFIG_ARM64_PTR_AUTH` 仍未开，FCM5 当前 arm64 段不要求它。
