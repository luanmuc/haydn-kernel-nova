# Nova 线说明

- 仓库：`luanmuc/haydn-kernel-nova`
- 分支：`haydn/nova`
- KSU：SukiSU-Nova `builtin`
- 管理器：`com.sukisu.nova`
- SUSFS：`v2.4.0`（5.4 移植，CI 构建通过；含 UID filter 命令接线，真机未验证）
- 对应 BakaSU 线：<https://github.com/luanmuc/haydn-kernel-bakasu>
- 下游补丁台账：`patches/nova/builtin-new/README.md`

## 发布标题

`[Nova][haydn] 5.4.302 ...`

## 禁止混刷

- 不刷 BakaSU 线包
- 不安装/保留 BakaSU 管理器后直接测试 Nova
