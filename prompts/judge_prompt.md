You are checking whether a Table-AGI final answer is correct.

Inputs:

- question,
- reference answer,
- submitted answer,
- answer type,
- optional tolerance.

Return JSON only:

```json
{"correct": true, "reason": "..."}
```

Use exact matching for arbitrary tokens. Use numeric tolerance only when the task declares a numeric answer type. Do not give credit for an answer that relies on a different interpretation of the question.
