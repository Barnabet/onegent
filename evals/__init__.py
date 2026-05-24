"""
Eval harness for the CIB agents library.

Each eval case is a YAML file under `evals/cases/<pack>/<case>.yaml`.
The runner spawns one supervisor run per case, then applies a list of
assertions to the resulting events + final text. Some assertions are
deterministic (`contains`, `regex`, `tool_called`); the `judge` assertion
calls a separate LLM as a rubric-graded reviewer.
"""
