# Evidence and limits

Captured on 2026-10-18 from the pinned released servers on macOS arm64.

- `environment.json`: installed versions, source pins, and credential-presence booleans.
- `probe-{early,middle,late}.json`: six actual MCP calls per stage, including service restart and persistent-state readback. No model was used; TF/PE/ECS are `null`.
- `model-preflight.json`: an actual blocked runner invocation because `AGENT_API_KEY` was not configured. It is not a completed task or a benchmark score.
- `manifest.json`: SHA256 of the original local files and the portable copies committed here.

Portable copies replace the absolute checkout directory with `<REPO>`. No tool arguments, outputs, IDs, scores, or errors are otherwise changed. `config_sha256` inside the preflight result belongs to its original configuration, before that path replacement. Use the manifest's portable-file digest to verify the committed copy. Original full outputs remain in ignored `results/raw/group-a-20261018/` on the development machine; teammates should generate their own outputs using the README commands.

The test suite also exercises the full adapter with a **fake local model HTTP service and real MCP servers**. Its scores are unit/integration protocol fixtures, not measurements, and are not included in these evidence files. A genuine model agent and model judge run remains pending service configuration.
