---
tool: repo.scaffold_skill
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, skill-authoring]
---

# repo.scaffold_skill

## Purpose
Create a new skill folder under `skills/<name>/` with a templated `SKILL.md`
and a populated `manifest.yaml` listing the tools the skill will require.

## When to use
- The skill_creator skill has gathered the skill's intended name, owner,
  classification, and the list of tools it will use, and all those tools
  already exist in the catalog.

## When NOT to use
- If any required tool is missing from the catalog — instruct the user to
  create the missing tool(s) first using `repo.scaffold_tool`.
- To modify an existing skill — this tool refuses overwrites.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Skill name, lowercase + underscores. |
| owner | string | yes | Owning team. |
| requires_tools | list[string] | yes | Exact tool names the skill will call. Validated against the registry. |
| classification | string | no | One of `public`, `internal`, `confidential`, `restricted`. Default `internal`. |
| data_sources | list[string] | no | Coarse data-source allow-list for audit reporting. |

## Returns
On success:
```
{
  ok: true,
  data: {
    skill: "<name>",
    created: ["skills/<name>"],
    next_steps: [...]
  }
}
```

## Errors
- `invalid_name` — name contains invalid characters.
- `already_exists` — `skills/<name>/` already exists.
- `unknown_tools` — one or more requested tools are not registered.

## Examples
### A skill reusing existing tools
Call: `repo.scaffold_skill(name="kyc_screening", owner="team-financial-crime-ai", requires_tools=["docstore.fetch", "text.summarize", "web.adverse_media_search"], classification="confidential", data_sources=["internal_docs", "public_web"])`
Returns: `{ok: true, data: {skill: "kyc_screening", created: ["skills/kyc_screening"], next_steps: [...]}}`

## See also
- `repo.scaffold_tool` — create any missing tools first.
- `repo.scaffold_pack` — wrap the new skill into a persona pack.
