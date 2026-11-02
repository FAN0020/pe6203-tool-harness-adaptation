# Capability consolidation — development result

Frozen source f60f96b; 10 product reviews committed e9e81e6 before score unblinding. Offline verifier checks 121 source files, 421 raw files, all 50 official score slots, native artifacts, and 124 settled requests.

| Same-condition group | SP completion | Candidate completion | SP complete products | Candidate complete products | TF SP → candidate | PE SP → candidate |
|---|---:|---:|---:|---:|---:|---:|
| Treated original 133 M/L | 2/2 | 0/2 | 0/2 | 0/2 | 9.7 → 9.2 | 8.0 → 4.8 |
| Frozen changed subset 133/283 M/L | 2/4 | 0/4 | 0/4 | 0/4 | 9.4 → 9.1 | 8.5 → 6.9 |
| Retention 235 L | 1/1 | 1/1 | 0/1 | 1/1 | 10 → 10 | 10 → 10 |

This exact version fails development and receives no independent validation. Math native calls rose to 37/21 from SP10/5 and both candidate answers were truncated. These observations do not establish why truncation occurred. Native-equivalence certification is insufficient evidence of equivalent agent behaviour or useful delivery. Unchanged retention knowledge makes its quality difference a run-level observation, not an adaptation gain.

Known new cost **USD0.253853268**, unknown requests0, model updater calls0. All412 actor native calls preserved;44 pre-registered native equivalence probes plus4catalog fetches were free. Original benchmark only; no synthetic success claim. Goal remains unmet.

Recompute: `uv run python results/evidence/capability-consolidation-20261102/verify_trial.py`. Generated code was reviewed statically and never executed. R07 missing promised implementation is conservatively unknown; even assigning that property pass cannot rescue completion or TF gates.
