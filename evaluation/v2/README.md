# evaluation 2

Original V2 evaluator source, protocol and user-supplied result evidence. The
engine is pinned to f90dbd57; the Selective algorithm is bdf0ccc5. Source hashes
were checked against the archived plan. This is a partial historical run: 27
planned trajectories, 25 scored, 125 judge slots, 19 normal completions. Unknown
charges remain unknown; no missing scores are filled.

`code/` contains byte-identical evaluation/runtime modules, `protocol/` holds
original inputs, and `archives/runtime.tar.gz` holds all pinned runtime, config
and CLI source. `recorded-results/` retains the published raw archive and its
original offline verifier.

Offline verification, from the repository root:

```sh
python evaluation/manage.py verify --version 2
python evaluation/v2/recorded-results/verify.py
python evaluation/manage.py extract --version 2 --artifact runtime --output outputs/evaluation2-source
```

Paid reruns must use the pinned source and explicit original CLI `experiment prepare`, `experiment run` and `experiment report` commands. Original V2 endpoint/provider variation is retained; this
is not a newly controlled V6-compatible comparison. Private API env files are
not included. The current V3 evaluation is pending and is not validated here.
