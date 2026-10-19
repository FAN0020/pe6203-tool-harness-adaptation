# Muchu Wu Sprint 1 baseline contribution

原始提交：`24adbf5`，分支：`baselines/wu-muchu-sprint1`。

已在原型基础上修复并迁入 [pe6203.baselines](../../../../src/pe6203/baselines.py)。
旧独立脚本和静态 synthetic validation dump 已由 [可执行测试](../../../../tests/test_baselines.py)
与 [真实 MCP 接入测试](../../../../tests/test_pipeline.py) 替代，避免维护两份实现。

提供 No Update 与 deterministic Full Rewrite；后者不是正式计划中的 LLM semantic rewrite。
原始贡献与 validation 记录仍保留在 Git 历史。

完整命令、修复说明和验证边界见 [baseline smoke](../../../../docs/baseline-smoke.md)。
