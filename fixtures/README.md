# Fixtures / 固定输入与初始状态

官方发布的 `anotation_path/` 已从锁定 commit 单独复制至本机 `.cache/mcpevol/fixtures/published-files/anotation_path/`，29 个文件，19,943,990 bytes。[Manifest](published-files.manifest.json)记录原始 bytes SHA256。目录只包含上游输入文件，不包含 task answers、参考轨迹或评分。

新 checkout 可在 bootstrap 后重建：

```bash
mkdir -p .cache/mcpevol/fixtures/published-files
cp -R .cache/mcpevol/upstream/anotation_path .cache/mcpevol/fixtures/published-files/
```

在本地 runner config 或 batch cell 指定 `"fixture_dir": ".cache/mcpevol/fixtures/published-files"`。Runner 拒绝 symlink，复制到每次新 workspace，保存逐文件 SHA256 与 manifest-object digest。正式实验只复制任务需要、已审查的文件，并冻结同一组内容。

**发布的文件存在不等于任务 fixture 完整。** `logs/`、requirements document、Horizon 既有项目等仍需逐任务核对，不将相似文件改名充当官方状态。Task 139 development smoke 从空目录新建状态，不需要把全部文件带入。
