# Environment API Specification

## Python interface

```python
from table_agi_bench.env.table_env import TableAGIEnv

env = TableAGIEnv(task, run_dir="runs/example")
obs = env.reset()
obs = env.step({"type": "move_cursor", "direction": "right", "steps": 1})
obs = env.step({"type": "answer", "value": "ZX-104"})
```

## Observation payload

The agent-facing observation should contain only safe fields.

```json
{
  "task_id": "rule_key_rank_000001",
  "question": "The KEY TABLE maps FOCUS to a target GROUP...",
  "image_path": "runs/example/obs_0003.png",
  "action_count": 3,
  "valid_actions": ["move_cursor", "move_viewport", "zoom", "answer", "noop"],
  "done": false,
  "feedback": null
}
```

### Safe fields

- `task_id`
- `question`
- `image_path` or base64 image bytes
- `action_count`
- `max_actions`
- `valid_actions`
- `done`
- `feedback` containing only generic messages such as `invalid_action` or `terminal`

### Unsafe fields

Never expose these to the agent:

- raw table cell values,
- row/column arrays,
- hidden answer,
- formula outputs,
- generator seed,
- parsed OCR,
- task template name if it reveals the rule,
- computed relevant rows,
- human baseline actions.

## Action contract

All actions count, including invalid actions and answer submission.

```json
{"type": "move_cursor", "direction": "up|down|left|right", "steps": 1}
{"type": "move_viewport", "direction": "up|down|left|right", "steps": 1}
{"type": "zoom", "value": "in|out"}
{"type": "select"}
{"type": "answer", "value": "..."}
{"type": "noop"}
```

## State transition policy

- The environment is turn-based.
- State changes only after an action.
- There is no asynchronous time pressure.
- The renderer produces a new image after every step.
- Invalid actions do not change state, but they do increment `action_count`.
- Wrong final answers terminate the task with score 0 for correctness.

## Recommended wrappers

Implement these wrappers after the MVP:

- `GymnasiumWrapper`: for RL/search agents.
- `OpenAIStyleAgentWrapper`: sends image observations and asks model for JSON actions.
- `HumanWebClient`: browser UI for baseline collection.
- `ReplayViewer`: visualizes traces and action decisions.
