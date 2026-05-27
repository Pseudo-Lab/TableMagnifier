# Agent Protocol

## Model prompt contract

The agent receives a question and an image observation. It must return exactly one JSON action per turn.

Valid responses:

```json
{"type":"move_cursor","direction":"right","steps":1}
```

```json
{"type":"move_viewport","direction":"down","steps":1}
```

```json
{"type":"answer","value":"KX-104"}
```

Invalid responses are converted to an invalid action and counted.

## Agent memory

The benchmark should not forbid internal memory. Agents may maintain notes, image summaries, or code-side state. These internal operations do not count as environment actions. Only calls to `env.step(...)` count.

## Baseline agents to implement

1. **RandomAgent**: sanity check.
2. **RasterScanAgent**: scans the whole sheet systematically, then answers using a supplied oracle for development only.
3. **HumanReplayAgent**: replays human traces; useful for UI regression and upper-bound checks.
4. **VisionLLMAgent**: sends image observations to a multimodal model and parses JSON actions.
5. **SearchAgent**: uses state hashes and exploration heuristics without raw table text.

## Important separation

Development-only oracle agents may access raw tables, but they must never be included in leaderboard runs or model prompts.

## Failure modes to log

- invalid JSON,
- unsupported action,
- repeated loop,
- max-action timeout,
- wrong answer,
- answer formatting error,
- evidence missed,
- arithmetic error,
- rule inference error.
