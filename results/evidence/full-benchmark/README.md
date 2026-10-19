# Full-benchmark environment evidence / 验证范围

2026-10-19，macOS arm64，官方 commit 与 release SHA256 见 [installation](installation.json)。**所有本目录记录均不是模型 benchmark 分数。**

| Evidence | 验证内容 | 限制 |
| --- | --- | --- |
| [全量 inventory](../benchmark-inventory.json) | 201 selected tasks；174 server-name union；每阶段文件与配置缺口 | 静态检查，不启动全部服务；ZIP hash 由 bootstrap 单独验证 |
| [installation](installation.json) | 三阶段完整 Node archive 解压与 SHA256 | package paths 含依赖副本；不包含 uv/uvx 服务安装 |
| [runtime](runtime.json) | Python、Node、host、Docker daemon 状态 | native stdio；未验证 container |
| [catalog index](../../../examples/catalogs/index.json) | 8×3 initialize/tools-list 全部成功 | 不证明业务调用成功 |
| [functional probes](functional-probes.json) | 新增 6×3 真实调用，17 pass / 1 failure；9 次持久化重启检查 | 无模型；Late thinking 保留官方报错 |
| [task readiness](task-readiness.json) | 全部任务的 profile / archive / fixture / 已知错误边界 | 实际模型评测均 not_run |
| [batch preflight](batch-preflight.json) | 3 个实际 CLI runs 因缺少凭据 blocked；resume 无重复 attempt | 0 模型调用；分数 null |
| [独立 checkout](independent-checkout.json) | Fresh clone + Python venv + 三阶段重新提取 smoke dependencies；38 tests passed | ZIP bytes 重用并重新验 hash，Node binary 重用；完整解压见 installation |
| [validation](validation.json) | lint、tests、文档/JSON/catalog/hash 检查与源码指纹 | fake model fixture 不构成模型效果评估 |

原有两服务的三阶段创建、重启、读取证据仍在[上级目录](../README.md)。完整现场 outputs 位于 ignored 的 `results/raw/full-benchmark/`；每次复现生成新目录。

`functional-probes.json` 只替换绝对 checkout 路径为 `<REPO>`；原始文件 bytes SHA256 与每组原始 calls 的 canonical-object hash 留在报告中，同时重算 portable calls hash。对象摘要使用 `benchmark.digest`，文件摘要使用原始 bytes，不能混比。Late thinking 的错误文本和其它调用结果没有改写。

实际 functional check 返回退出码 2，因为发现发布包缺陷。保留此结果，不将检查改成“全部成功”。所有测试通过只表示 adapter 遵守所测契约，不消除上游缺陷或服务凭据缺口。
