# Human Baseline Protocol

## Purpose

Human baselines are needed because the benchmark is about efficient adaptation, not only correctness. The same task can be solved correctly by exhaustive navigation, but that should score lower than a human-like efficient solution.

## Participants

Use at least 10 participants per environment or task family for paper-quality baselines. Participants do not need table-analysis expertise, but they should be comfortable reading spreadsheets.

## Session flow

1. Consent and short explanation of controls.
2. Two public practice tasks that are not used in scoring.
3. Scored tasks in randomized order.
4. Optional post-task difficulty rating.

## Data to collect

- participant ID hash,
- task ID,
- start time and end time,
- action trace,
- final answer,
- correctness,
- total action count,
- invalid action count,
- task difficulty rating.

## Baseline computation

For each task:

```text
human_mean_actions = mean(action_count of correct human runs)
human_second_best_actions = second-lowest action_count among correct human runs
human_median_actions = median(action_count of correct human runs)
```

If fewer than 8 humans solve a task correctly, mark the task as failed calibration and revise it.

## Inclusion criteria

A task can enter the benchmark if:

- at least 80% of humans answer correctly within max actions,
- answer ambiguity is not reported by multiple humans,
- median human time is within the target session budget,
- no UI bug or rendering issue appears in traces.

## Paper reporting

Report the number of humans, calibration pass rate, mean actions, median actions, second-best actions, and error reasons from failed calibration tasks.
