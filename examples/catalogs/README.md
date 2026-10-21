# Complete reviewed catalogs / 完整工具目录

[索引](index.json)来自 pinned 发布包的真实 MCP `initialize → tools/list`：8 services × Early/Middle/Late，共 24 份。索引列出 server ID、工具数、路径与 canonical-object SHA256；没有任务答案、评分或 mutation labels。

| 目录 | 用途 |
| --- | --- |
| `early/`、`middle/`、`late/` | 单服务器完整 catalog，文件名为 server ID 的 SHA256 前 12 位 |
| `task103/`、`task105/`、`task139/`、`task283/`、`task393/` | 按官方固定 server set 合并完整 catalog；每组包含三阶段与来源索引 |
| `task139/early.json` | development 的完整 K0：40 tools；Middle 40，Late 44 |

No Update 在三个阶段都使用 Early K0；B/C 方法从同一完整 K0 出发。旧 `examples/knowledge/` 的四工具样例仍保留，仅供历史 smoke 复现。

目录导出成功不证明工具执行或任务成功。Late thinking 的运行错误、fixture 缺口与全量服务审查状态见 [全量交接](../../docs/full-benchmark.md)。各服务描述/schema 均为第三方 metadata，执行前仍按 reviewed profiles 限制运行范围。
