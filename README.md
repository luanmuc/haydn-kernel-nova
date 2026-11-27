# haydn-kernel-nova

> **本仓库只维护 SukiSU-Nova builtin 线（Nova 线）。**
>
> BakaSU 稳定线在另一个独立仓库：  
> https://github.com/luanmuc/android_kernel_xiaomi_sm8350_miyume
>
> 两条线不要混刷；Nova 线使用 `com.sukisu.nova` 管理器。

## KSU 版本线

- 分支：`haydn/nova-builtin-new`
- KSU：SukiSU-Nova `builtin-new`，固定 `5a3ec414`
- SUSFS：`v2.4.0`（GKI 5.10 核心移植到 5.4；已真机验证）
- 管理器：`com.sukisu.nova`
- 适用设备：Redmi K40 Pro / Pro+（haydn）
- 当前正式版：`07e07dff3` / run `45918531589`（success，[Release](https://github.com/luanmuc/haydn-kernel-nova/releases/tag/haydn-07e07dff3-official-2026-11-27)）
- 禁止：不要刷 BakaSU 线的包，不要与 BakaSU 管理器混装

---

## Xiaomi SM8350 Device MiYume HoshinoNeko Kernel ##

## 维护设备 ##
- Xiaomi 11 (venus)
- Xiaomi 11 Pro (mars)
- Xiaomi 11 Ultra (star)
- Redmi K40 Pro(+) (haydn)

## 内核特性 ##
- 版本：5.4.302
- 更多描述在 Releases

## 相关配置 ##
- **Venus** 使用 `venus_defconfig`
- **Star/Mars** 使用 `star_defconfig`
- **Haydn** 使用 `haydn_defconfig`

## 默认配置 ##
- Clang 18.1.8 & LLD 18.1.8

## 开始编译 ##
bash build_device.sh (填设备代号, 不填默认venus)
