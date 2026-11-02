# Selective V1 integration record

Original feature tip: `4a16b56a61599a781bf617819ef14253714c941e`.
Original implementation: `fbc46c2db18b0cc78fcb307df2c6df0a6626ce6a`.

Main already contains the integrated deterministic V1 implementation. This merge
retains the current validated implementation, exact target-ID validation and
explicit rejection of the old unvalidated optional LLM path. The historical
branch and its authorship are preserved in merge ancestry. The patch here records
the meaningful legacy implementation differences, rather than duplicating the
source tree or replacing current shared baselines, CLI, protocols or evaluation.
The old upstream agent copy and obsolete updater template are not installed as
additional runtime implementations. Historical records remain available with
`git show 4a16b56a:path`.

This directory is historical documentation, not additional executable code and
not part of source-line contribution percentages.
