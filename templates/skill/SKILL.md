---
name: <skill_name>
description: >
  Use this skill when <concrete triggers>. Lead with the triggers, name the
  inputs ("a .xlsx file", "a counterparty id"), and name the output ("a
  screening note", "a draft memo"). Negatively scope where the skill could
  be confused with a neighbour ("do not use for individuals — see pep_screen").
version: 0.1.0
---

# <Skill name>

## When this skill applies
Fuller prose version of the description. This is the model's first read after
activation; make the trigger conditions unmistakable.

## Workflow
A numbered procedure. Reference tools by their exact registered name.

1. Step one with `domain.tool_name(arg=...)`.
2. Step two with `other.tool(arg=...)`.
3. Final assembly using `references/<template>.md` if applicable.

(No shell. No install. No "run this script". Every action is a tool call.)

## Conventions
Style, formatting, tone, units, naming conventions. The things a senior
analyst would tell a junior at the start of a project.

- Bullet one.
- Bullet two.

## Edge cases
- If <tool> returns `error.code = "<code>"`, do <X> rather than <Y>.
- If <ambiguous condition>, ask the user to clarify before continuing.

## References
- `references/<file>.md` — describe what's in it and when to load it.
