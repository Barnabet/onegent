# Evals

The eval harness measures end-to-end behaviour of a pack against a fixed set
of cases. Each case is one user message + a list of assertions; the runner
spawns a real supervisor run and scores the outcome.

## Layout

```
evals/
  cases/
    <pack>/
      <case_id>.yaml       # one case per file
  results/
    <timestamp>.jsonl      # one line per case (git-ignored)
  case.py                  # YAML loader
  score.py                 # deterministic scorers
  judge.py                 # LLM-as-judge scorer
  runner.py                # runs a suite via the supervisor
  report.py                # terminal + JSONL output
```

## A case file

```yaml
id: hello_echo_smoke           # globally unique
pack: hello                    # must match a packs/<pack>.yaml
description: One-line summary.
user_message: "Echo 'foo'."
timeout: 60                    # supervisor wall-clock cap (s)
assertions:
  - kind: no_error
  - kind: tool_called
    name: core.echo
    min_times: 1
    args_contains: { text: "foo" }
  - kind: contains
    text: foo
    case_sensitive: false
  - kind: regex
    pattern: "\\bfoo\\b"
    flags: [i]
  - kind: tool_not_called
    name: repo.scaffold_tool
  - kind: judge
    threshold: 4               # 1..5 from the rubric
    criterion: >
      The reply echoes "foo" verbatim and confirms the tool was used.
```

### Assertion kinds

| kind              | what it checks                                                 |
| ----------------- | -------------------------------------------------------------- |
| `no_error`        | The supervisor returned no `error`; no `error` events emitted. |
| `contains`        | Substring in `final_text` (case-insensitive by default).       |
| `regex`           | Regex match on `final_text`; flags = subset of `i`, `m`, `s`.  |
| `tool_called`     | Tool invoked `>= min_times`; optional shallow `args_contains`. |
| `tool_not_called` | The named tool must not appear in the transcript.              |
| `judge`           | LLM scores the reply 1–5 vs `criterion`; pass if `>= threshold`. |

A case passes only when **every** assertion passes **and** the supervisor
reported no error.

## Running

```bash
# All cases for all packs (uses CLIProxyAPI on LLM_BASE_URL).
python scripts/eval.py

# One pack.
python scripts/eval.py --pack credit_analyst

# One case, no LLM-judge (deterministic checks only — fast, free).
python scripts/eval.py --case hello_echo_smoke --no-judge
```

The runner writes `evals/results/<timestamp>.jsonl` unless you pass
`--no-write`. Each line is a `CaseResult` (case id, pass/fail, per-assertion
breakdown, judge rationale, stats, final text).

## LLM-as-judge

The `judge` assertion calls the same chat endpoint with a strict rubric
(see `evals/judge.py`). It sees the user message, the final reply, and a
brief tool-call summary (names + arg keys only, never raw payloads). The
judge must reply with strict JSON:

```json
{"score": 4, "rationale": "Concise and addresses the criterion fully."}
```

Override the judge model via `EVAL_JUDGE_MODEL`; otherwise it uses the same
default as `runtime.llm`. Use a *different* model for the judge than the
agent when you can, to reduce self-grading bias.

## Adding a new case

1. Pick a pack and a behaviour you want to lock down.
2. Drop a YAML file in `evals/cases/<pack>/<descriptive_id>.yaml`.
3. Start with `no_error` + at least one deterministic assertion
   (`tool_called`, `contains`, or `regex`). Add a `judge` rubric only for
   open-ended quality checks the deterministic ones can't capture.
4. `python scripts/eval.py --case <id>` to verify it runs.
5. Commit.

## Offline tests

`tests/test_evals.py` covers the case loader, scorer, and judge parser
without touching the LLM or supervisor — these run as part of `pytest`.
