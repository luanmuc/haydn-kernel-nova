# VINTF 诊断版 469e7e420（CFI permissive + PAuth）

日期：2026-11-26
状态：**诊断版，不是正式修复版**。用于确认黑屏是否由严格 CFI / 缺少 PAuth 引起。

## 与上一版差异

- 新增 `CONFIG_CFI_PERMISSIVE=y`
- 新增 `CONFIG_ARM64_PTR_AUTH=y`
- 继续保留 `CONFIG_CFI_CLANG=y`、`CONFIG_SHADOW_CALL_STACK=y`，VINTF FCM5 仍是 y
- 内核代码、KSU、SUSFS 不变

## 构建

| 项 | 值 |
|---|---|
| 分支 | `haydn/nova-vintf-fix-diag` |
| 提交 | `469e7e42072cb0e0a54221229e05b29a36c3aa84` |
| run | `45654852987` |
| 结果 | Success |
| 总耗时 | 32:39 |
| 编译耗时 | 29:12 |
| build log | 15 warnings / 0 error |
| Image | 54,663,680 bytes，SHA256 `37e0431cf047acb8c8c7a1fc242988e6535872672560b787c70246f049f44cc4` |
| clean boot | 201,326,592 bytes，SHA256 `90a90d760c44e8cb9eb9777cfc7b4063261d1455c5ce410074373f7a7837f94b` |
| boot 内 kernel | 与新 Image 一致 |
| boot 内 ramdisk | `29254f09fe5c79a859430bb4f432d7c20afda0821121f6f40eeeb2f808cfa446`（旧 clean ramdisk） |

## AVB

```text
Algorithm: NONE
Original image size: 74,567,680
VBMeta offset: 74,567,680
Salt: 4ce0907ef73ae9cceb8607c9681846e43c96d8c2fa20b92b9a1ea3c4d02d71be
```

`avbtool verify_image`：footer / NONE vbmeta 与 sha256 hash 均通过。

## 测试

```bash
fastboot boot Nova-haydn-patched-clean-boot-diag-469e7e420.img
```

观察：

1. 是否仍然出现“OKAY → 黑屏 → 重启 → 小米 logo → 原系统”
2. 如果这次能过黑屏，是否出现“您的设备内部出现了问题”弹窗
3. SukiSU 是否工作中
4. Wi-Fi / 蓝牙 / 相机 / 指纹 / 触摸 / 扬声器 / 充电 / USB

## 构建缓存说明

- Clang 缓存命中：没有重新下载 996MB 工具链
- ccache 恢复的是 `ccache-haydn-45416356639-1`，属于 GitHub 默认分支 `haydn/nova` 的旧 190MB 缓存
- 本次 ccache：`4302 / 12521 = 34.36%` 直接命中，primary 50.26%，miss 8219，uncacheable 5043
- 临时分支看不到 `haydn/nova-builtin-new` 的 490MB ccache，这是命中率不高的主要原因
- AnyKernel3 缓存首次 miss，构建成功后已保存，下次会命中

## 如果还黑屏

下一步做 **关闭 `CONFIG_SHADOW_CALL_STACK`** 的对照构建；再不行就关 CFI 对照。先确认是哪一项导致早期启动失败，不靠猜。
