# llm-exp

Low-token experiment harness with Python stdlib and POSIX shell only.

- `run --label NAME -- CMD...` captures full output to `LLM_EXP_ROOT/raw/<timestamp>-NAME.log`, writes command metadata, and prints only status, elapsed time, selected useful lines, and log paths.
- `summarize-failure RAW OUT` preserves the raw log and writes at most 50 contextual lines around failure signatures.
- `sysmon OUT.jsonl SECONDS [PID]` samples macOS memory pressure, vm statistics, swap, disk free space, and optional process RSS/CPU; adjacent `.stats.json` is compact.
- `registry.py RESULTS.jsonl RECORD.json` validates/appends the required experiment schema.
- `compare RESULTS.jsonl` renders a compact table.

Validation target: one passing and one failing command, both retained under the campaign raw directory. For output-heavy commands, compact summaries reduce normal interactive log exposure from full command output to roughly 10–25 lines; actual reduction is measured in the campaign validation record.
