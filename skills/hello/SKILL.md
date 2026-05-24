---
name: hello
description: >
  Use this skill when the user asks for a connectivity / smoke-test of the
  agent platform — typically phrases like "say hi", "ping", "smoke test",
  "are you alive". The skill calls a no-op echo tool to prove the tool
  plumbing works end-to-end, then reports success.
version: 0.1.0
---

# Hello

## When this skill applies

The user wants to verify the agent + tool plumbing is alive. They are not
asking for any real work to be done.

## Workflow

1. Call `core.echo(text="hello from the agent")` exactly once.
2. If the tool returns `ok: true`, reply with a short confirmation:
   "Platform is alive. Tool round-trip succeeded."
3. If the tool returns `ok: false`, surface the error code and message
   verbatim and stop.

## Conventions

- Keep the final reply to one or two sentences. This skill exists only as
  proof of life.
- Do not call any other tool. Do not call `core.echo` more than once.

## Edge cases

- If the user's message clearly asks for real work, do not use this skill;
  another skill should handle it.
