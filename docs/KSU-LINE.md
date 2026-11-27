# Nova 线说明

- 仓库：`luanmuc/haydn-kernel-nova`
- 默认 / 唯一主线：`haydn/nova-builtin-new`
- KSU：SukiSU-Nova `builtin-new`，子模块固定 `5a3ec414`，内核显示 `30007-6`
- 管理器：上游 `v3.0.0`，`35000-6`，包名 `com.sukisu.nova`
- SUSFS：`v2.4.0 (SUSFS Inline Hook)`，已随 `07e07dff3` 正式版真机验证
- 当前正式 tag：`haydn-07e07dff3-official-2026-11-27`
- 对应 BakaSU 线：<https://github.com/luanmuc/haydn-kernel-bakasu>
- 下游补丁台账：`patches/nova/builtin-new/README.md`

## 发布标题

`[Nova][haydn] 5.4.302 ...`

## 发布资产

按 [`RELEASE-STANDARD.md`](RELEASE-STANDARD.md) 执行：AK3、clean boot、上游配套 APK、Image、config、build log、RELEASE、`SHA256SUMS`。

## 禁止混刷

- 不刷 BakaSU 线包。
- 不安装或保留 BakaSU 管理器后直接测试 Nova。
- 不使用本地旧管理器 APK；管理器必须取上游对应 Release 的 arm64-v8a 包。
