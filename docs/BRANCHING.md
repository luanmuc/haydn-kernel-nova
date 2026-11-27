# 分支模型

本仓库只保留一条主线：

`haydn/nova-builtin-new`

## 规则

- GitHub 默认分支就是 `haydn/nova-builtin-new`。
- 所有构建、验证、正式 tag 和 Release 都从这条主线产生。
- 不再保留 `haydn/nova`、`haydn/stable`、`haydn/test` 等长期并行分支。
- 临时诊断分支只在排查期间存在，结论写回 `docs/` 或补丁台账后删除。
- 发布 tag 必须指向主线 commit；具体资产要求见 [`RELEASE-STANDARD.md`](RELEASE-STANDARD.md)。

## 历史收口

- `haydn/nova` 的文档历史已并入主线，分支已删除。
- `haydn/nova-fcm6` 已删除，FCM6 正式版作为历史 Release 保留。
- `haydn/nova-builtin-new-b1-cfi` 已删除，CFI 试验结论保留在诊断文档中。
- 不再为单个修复或试验长期保留支线；修复直接进主线并用补丁台账记录。

## 发布流程

```bash
git checkout haydn/nova-builtin-new
git pull --ff-only origin haydn/nova-builtin-new
bash scripts/ci/release.sh <tag> "<标题>" <body.md>
```

`release.sh` 会校验 tag、构建 run 和产物；正式发布前建议先跑 `DRY_RUN=1`。
