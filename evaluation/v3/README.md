# evaluation 3 — verified optimized V3, 2026-11-03

This package supersedes the former pending staging state after the explicitly
authorized new evaluation. It publishes the actual evaluator source and frozen
runtime from selective-V3 f63f4cd, with the completed knowledge-only study.

Four original MCPEvol-Bench tasks (430/133/90/235), Early/Middle/Late,
No Update/Full Rewrite/optimized V3, three independent actor executions per cell:
108 trajectories, 540 official-rubric ratings, all scored. No extra Python
artifact validation/repair was enabled. No Update had one empty final answer;
all original grades and negative outcomes are retained. This is not a claim of
full safety or universal strategy superiority.

| Strategy | TF /10 | PE /10 | Actor + one-time update USD |
|---|---:|---:|---:|
| No Update | 9.483 | 7.622 | 0.309394212 |
| Full Rewrite | 9.789 | 8.483 | 0.367303716 |
| V3 | 9.906 | 8.728 | 0.338417184 |

Judge costs are evaluation overhead. Actual total fees: USD 1.277705820,
960 receipts, unknown charges zero. Source/knowledge/question/receipt
verification passed. See recorded-108/interpretation.zh-CN.md and summary.json.

- code/: byte-identical evaluator script copies, with source provenance.
- archives/runtime.tar.gz: the standalone evaluated source/config runtime.
- protocol/: exact frozen input plan and metadata/knowledge identities.
- recorded-108/: original complete results, raw archive and verification.
- scope-input/: earlier finite before/after input diagnostics, not task scores.
- integration-verification.json: latest-main merge tests and compatibility.
- historical-pending-*: the superseded unavailable state, retained for history.

Main retains its existing default and all other version entries; request
--selective-mode hybrid_v3 to select the optimized implementation. Merger does
not imply it is the best method in every setting. The legacy 22/27-score V3
study is distinct and remains under results/qi-v3/ranlufei-eval-20261103/.

Offline commands (no model requests):

    python evaluation/manage.py verify --version 3
    python evaluation/manage.py extract --version 3 --artifact runtime --output outputs/v3-evaluated-source

Paid reproduction must use a fresh output directory and the archived protocol,
matching installed MCPEvol services and separately supplied credentials.
The code copies do not silently rewrite historical local paths or install tools.
