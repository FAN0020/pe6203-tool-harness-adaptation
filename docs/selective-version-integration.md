# Selective Patch version integration

This integration preserves the original commits and avoids separate copies of
shared runtime code. Main's deterministic default and existing research variants
remain available. No Update and Full Rewrite algorithms are unchanged. The shared
artifact loop is opt-in, never automatically enabled for existing experiments.

| Version | Original tip | Runtime location and entry |
| --- | --- | --- |
| V1 | `4a16b56a` | `selective.py`; `--selective-mode deterministic_v1` |
| V2 | `bdf0ccc5` | `hybrid_selective.py`; `--selective-mode hybrid_v2` |
| V3 | `b94d5122` | `capability.py`; `--selective-mode hybrid_v3`; artifact plan/validation commands |
| V5 | `403783a6` | `selective_v5.py`, shared evidence/rules/scope modules; `--selective-mode hybrid_v5`, `run-v5`, `collect-v5-probes` |
| V6 | `6437fb3c` | `selective_v6.py`, `payload_v6.py`, `execution_v6.py`; `--selective-mode hybrid_v6`, `run-v6` |

## Conflict resolution

V1 was already imported into main through integration commits. Main's stronger
validation and disabled unvalidated legacy LLM path are retained. Historical
implementation differences are recorded in `contributions/haoqi/history/selective-v1/`;
the old source tree and upstream agent are not duplicated. Existing shared README,
handover, configuration and protocol updates are retained rather than reverted to
old feature-branch copies.

The V2/V3/V5/V6 dispatch branches and CLI commands are combined. Shared artifact
validation exists once, with V3 and V5/V6 execution entries reusing it. V5's later
scope/token optimisation is retained alongside V6's separate screening mechanism.
Version-specific tests select their mode explicitly; integration tests check all
modes and compatibility of the old default. Historical scores remain historical.

## Contribution and evaluation provenance

Hao Qi designed and developed V1, V2, V3, V5 and V6 and reports responsibility for
the V2/V3/V5/V6 evaluations. Git author records identify who committed a file;
they do not by themselves establish who designed or ran an experiment. In
particular, V3 contains evaluation summaries committed by `ranlufei1011-code` and
Hao Qi's implementation commits. Their original authorship and evidence are
preserved, without changing experiment ownership solely from the submitter name.

This integration makes no claim of benchmark superiority. Archived evaluations,
implementation acceptance, finite artifact tests and ongoing runs must remain
separate when interpreting results. Runtime source attribution should count
tracked `src/**/*.py` with a stated Git revision and denominator, excluding this
history folder, generated outputs, dependency copies and literature/report files.
