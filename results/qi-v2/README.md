# QI-V2 acceptance records

This directory contains implementation checks, **not a V2 benchmark**.
`TF`, `PE`, `ECS`, recovery and retention have not been measured for V2.
Historical V1 results remain unchanged.

| Attempt | Provider | Outcome | Meaning |
| --- | --- | --- | --- |
| local-acceptance-01 | Explicit local HTTP API double | Acceptance failed | Initial fixture's generic source name also matched the consumer rule, so it did not establish selection outside the deterministic impact set. |
| live-smoke-01 | Real DeepSeek through OpenRouter | Acceptance failed | One request; model kept the old consumer rule because the initial fixture did not establish a clear source-to-consumer relationship. The API/CLI ran, but the required implicit-dependency check failed. |
| local-acceptance-02 | Explicit local HTTP API double | Passed | Revised, explicit balance-service/display flow; exercises actual SDK and default CLI dispatch, review, patch, argument cases and preservation. Scripted responses are not real reasoning evidence. |
| live-smoke-02 | Real DeepSeek through OpenRouter | Passed | Two requests; full three-record review, semantic selection outside the rule-based impact set, local usage-rule edit, three argument regressions and unrelated-record preservation. One synthetic example only. |

Each attempt retains its configuration, limits, CLI output, acceptance result,
knowledge (when structurally accepted), complete requests/responses and costs.
A method run may be structurally accepted while the **additional acceptance
expectation** fails; that distinction is visible in the first two records.
Failed acceptance attempts were neither deleted nor retroactively relabeled.
The original input evidence is preserved in the requests and deterministic diff;
the current `examples/qi-v2` files are the revised fixture used for attempt 02.

The real provider reported $0.000396165 for live 01 and $0.00058516 for live 02:
**3 actual requests, $0.000981325 total**. Local double tokens are synthetic and
its omitted provider cost is recorded as null; they are excluded from real
spending. Local-double audit phase names are real program phases, not claims
that a real model was invoked.

`pytest.xml` records the final offline test suite. The suite includes an exact
request comparison replay of the recorded live-02 responses against the current
pipeline: it makes no new provider calls and confirms the model inputs still
match after source hardening. It does not count as another live model test.

`slide4-verification.json` compares complete before/after PPTX exports. Only
slide 4's content/formatting and speaker notes changed. Google renumbers image
files and regenerates table-style GUIDs, so the verifier resolves them to actual
image bytes and table-style definitions; no formatting difference is ignored.
`slide4-speaker-notes.txt` is the updated English script and nonspoken reference.

See `../../docs/qi-v2-selective-patch.md` for the workflow, commands and limits.
