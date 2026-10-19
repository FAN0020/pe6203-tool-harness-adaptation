# 报告与贡献记录模板

复制 [report.md](report.md) 到 `results/raw/<experiment_id>/report.md` 填写；审查脱敏后连同证据放入 `results/evidence/<experiment_id>/`。模板中的 `—` 表示待填写，不是零分或结果。

| 表 | 从哪里取数 | 校验 |
| --- | --- | --- |
| 实验身份 | freeze record / manifest / Git commit | 配置是否真正冻结；是否为真实模型运行 |
| TF / PE / ECS | 配对完整 EVAL 与 ledger | 5 次有效 judge；ECS 三阶段完整；单位和 std 口径 |
| Recovery / retention | 冻结前变化标签 + 配对分数 | changed / unaffected 分开；uncertain 不硬分组 |
| 成本 | provider usage、updater artifact、已核定价格 | 去重；缺失为 unknown；列全部尝试成本 |
| 失败案例 | patch + model/tool trace + judge | under / over-update 必须有因果依据 |
| 个人贡献 | commits、本人实现、验证与运行记录 | 团队成绩与本人贡献分别写 |

报告从原始证据重建，不从预期结论倒填数字。正式实验未完成前，保留缺口状态。
