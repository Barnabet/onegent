---
tool: repo.scaffold_pack
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, pack-authoring]
---

# repo.scaffold_pack

## Purpose
Create a new pack YAML at `packs/<name>.yaml` that bundles one or more
existing skills for a persona.

## When to use
- The skill_creator skill has confirmed the persona, the list of skills,
  the classification ceiling, and the model id.

## When NOT to use
- If any listed skill does not exist — create the skills first using
  `repo.scaffold_skill`.
- To modify an existing pack — this tool refuses overwrites.
- For packs at `confidential` or above without first agreeing on a risk
  review process — this tool will create the pack but will NOT fill in
  `risk_review` for you; the user must add it before the pack will load.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Pack name, lowercase + underscores. |
| owner | string | yes | Owning team. |
| description | string | yes | One paragraph on the persona this pack serves. |
| skills | list[string] | yes | Skill names already on disk. Validated. |
| classification | string | no | Default `internal`. |
| model | string | no | Pinned model id, default `claude-sonnet-4-6`. |
| allowed_data_sources | list[string] | no | Coarse allow-list. |

## Returns
On success:
```
{
  ok: true,
  data: {
    pack: "<name>",
    created: ["packs/<name>.yaml"],
    next_steps: [...]   # includes a reminder about risk_review for confidential+
  }
}
```

## Errors
- `invalid_name` — name contains invalid characters.
- `already_exists` — pack file already exists.
- `unknown_skills` — one or more listed skills are not on disk.

## Examples
### A simple internal-class pack
Call: `repo.scaffold_pack(name="credit_analyst", owner="team-credit-ai", description="Credit analysts drafting and reviewing corporate credit memos.", skills=["credit_memo", "xlsx_handling"], classification="internal")`
Returns: `{ok: true, data: {pack: "credit_analyst", created: ["packs/credit_analyst.yaml"], next_steps: [...]}}`

## See also
- `repo.scaffold_skill` — create any missing skills first.
- `repo.scaffold_tool` — create any missing tools first.
