# Evaluation Metrics

## Primary metrics

### 1. Answer Accuracy

A task is correct if the submitted answer matches the reference answer under the answer normalizer for the task type.

Supported types:

- string / token,
- integer,
- float with tolerance,
- boolean,
- ordered list,
- unordered set.

### 2. Human-normalized Action Efficiency

Let:

- `a_t` = agent actions on task `t`, including answer submission.
- `h_t` = human baseline actions for task `t`.
- `c_t` = 1 if answer is correct, otherwise 0.
- `p` = penalty exponent, default 2.

The task efficiency score is:

```text
Eff_t = c_t * min(1, h_t / a_t) ^ p
```

This gives 0 for wrong answers. It caps at 1 so an exploit or unusually short route cannot dominate the benchmark.

### 3. Benchmark Score

```text
Score = mean_t(Eff_t)
```

For level-based environments, compute level scores first and then a weighted environment average.

```text
EnvScore_e = sum_l(w_l * Eff_l,e) / sum_l(w_l)
```

Use `w_l = l` so later, harder levels count more.

## Human baseline options

Because the target project wants to compare to average human actions, store both:

- `human_mean_actions`: primary Table-AGI baseline.
- `human_second_best_actions`: secondary ARC-style baseline.
- `human_median_actions`: robustness check.

Recommended paper reporting:

- Main table: accuracy, mean-action efficiency, second-best-action efficiency.
- Appendix: median baseline, per-task action distributions.

## Suggested human protocol

- Recruit at least 10 human testers per environment or task family.
- Use the same UI, action space, and images as the AI agent.
- Hide answers and generator metadata.
- Log every action.
- Exclude tasks where fewer than 80% of humans solve within max actions.
- Use practice tasks from the public demo split before measuring.

## Cutoffs

Set max actions per task to reduce brute forcing and cost.

Recommended default:

```text
max_actions_t = ceil(5 * human_mean_actions_t)
```

If no human baseline exists yet, use a provisional generator-estimated budget and mark results as non-final.

## Diagnostics

Report all of the following:

- Accuracy by task family.
- Efficiency by task family.
- Action count distribution.
- Invalid action rate.
- Number of viewports visited.
- First relevant evidence action index, if a verifier can compute it.
- Cursor distance traveled.
- Whether failure was due to perception, navigation, arithmetic, rule inference, or answer formatting.

## Leaderboard columns

| Column | Meaning |
|---|---|
| `Accuracy` | fraction of tasks answered correctly |
| `Eff-MeanHuman` | mean human-normalized efficiency using human mean actions |
| `Eff-SecondBest` | ARC-style human-normalized efficiency using second-best human |
| `MeanActionsCorrect` | mean actions on correct tasks |
| `Cost` | model/API/computation cost per full run |
| `InvalidActionRate` | invalid actions / total actions |
