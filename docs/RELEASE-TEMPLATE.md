# Nova 线发布说明模板

标题：

```text
[Nova][haydn] 5.4.302 <版本号>
```

正文必须包含：

- 版本线：SukiSU-Nova builtin 线
- KSU：SukiSU-Nova `builtin-new` / `<commit>` / 内核显示版本
- SUSFS：`v2.4.x` 及验证状态
- 管理器：上游版本、`com.sukisu.nova`、APK 文件版本
- 内核：`5.4.302-HoshinoNeko-nova-...`
- 仓库：<https://github.com/luanmuc/haydn-kernel-nova>
- 分支：`haydn/nova-builtin-new`
- 提交：`<commit>`
- 构建 run：`<run url>`
- SHA256：`<sha256>`
- 适用设备：Redmi K40 Pro / Pro+（haydn）

必须包含“禁止混刷”：

- 不刷 BakaSU 线包
- 不与 BakaSU 管理器混装
- 切换线前卸载旧管理器并重启
- 不使用本地旧管理器 APK

正式资产必须按 [`RELEASE-STANDARD.md`](RELEASE-STANDARD.md) 发齐 8 件：

- AnyKernel3
- clean boot
- 上游配套 APK
- Image
- config
- build log
- `RELEASE-<sha>.md`
- `SHA256SUMS`
