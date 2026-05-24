# Tool catalog

Generated from the live tool registry. Do not edit by hand.
Re-render with `python scripts/check_catalog.py --write`.

**11 tools** across **5 domains**.

## By domain

### `core`

#### `core.echo` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: core.echo
version: 1
owner: team-platform-ai
classification: [public]
tags: [diagnostic, smoke-test]
---

# core.echo

## Purpose
Return the input string unchanged. Used only for smoke-tests of the agent
loop and tool plumbing.

## When to use
- The user asks you to "echo" a specific string back to them verbatim.
- A skill explicitly instructs you to call `core.echo` as a connectivity check.

## When NOT to use
- For any real task. This tool does no useful work.
- To repeat the user's message back in a conversational reply — just include
  the text in your own response, no tool call needed.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The exact string to echo back. Keep it short (< 200 chars). |

## Returns
On success: `{ok: true, data: {echoed: "<text>"}}`

## Errors
- `invalid_input` — `text` missing or not a string.

## Examples
### Smoke-test call
Call: `core.echo(text="hello")`
Returns: `{ok: true, data: {echoed: "hello"}}`

## See also
- (none — this tool exists in isolation for diagnostics.)

</details>

### `docstore`

#### `docstore.fetch` &nbsp; <sub>v1 · confidential · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: docstore.fetch
version: 1
owner: team-platform-ai
classification: [confidential]
tags: [docstore, fetch, read, internal-docs]
---

# docstore.fetch

## Purpose
Retrieve a document from the bank's internal document store by id, entity
name, or short free-text query. Returns the document body plus metadata.

## When to use
- A skill needs to pull a specific internal document — a KYC dossier, a
  credit file, a counterparty profile — to operate on it.
- The user gives you an entity name or an id and asks you to "fetch" or
  "pull up" the dossier.

## When NOT to use
- For searching the open web — use `web.search` (when available).
- For reading repository docs (authoring guides, catalogs) — use
  `repo.read_doc`.
- For reading a local spreadsheet path the user has attached — use
  `xlsx.read` or `text.read_file` (when available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | An id (e.g. `"globex-kyc-2025"`), an entity name, or a short free-text term. |
| doc_type | string | no | Restrict to a specific type, e.g. `"kyc_dossier"`, `"credit_input"`. |
| latest | bool | no | When multiple match, return the most recently published. Default `true`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    id: "...",
    doc_type: "...",
    entity: "...",
    published: "YYYY-MM-DD",
    body: "<full document text>"
  }
}
```

## Errors
- `store_empty` — the document store is empty (configuration issue).
- `not_found` — no document matched the query.
- `file_missing` — the index references a file that is not on disk.

## Examples
### Fetch a KYC dossier by entity name
Call: `docstore.fetch(query="Globex Corporation", doc_type="kyc_dossier")`
Returns: `{ok: true, data: {id: "globex-kyc-2025", entity: "Globex Corporation SA", ...}}`

### Fetch a credit input file by id
Call: `docstore.fetch(query="acme-credit-input")`

## See also
- `repo.read_doc` — for repository docs, not internal documents.
- `xlsx.read` — when the user has attached an .xlsx file directly.

</details>

### `repo`

#### `repo.read_catalog` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.read_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, read, reference]
---

# repo.read_catalog

## Purpose
Return the live catalog of every registered tool and discovered skill as
structured data: names, owners, classifications, tags, and purpose lines.

## When to use
- A skill needs to know what tools exist (e.g. the skill_creator before
  proposing a new tool).
- You need a quick inventory before deciding what to build.

## When NOT to use
- When you want to find tools matching a specific need — use
  `repo.search_catalog`, which scores by relevance.
- When you want the raw markdown of a tool card — read the card directly via
  the catalog entry's tool name + your knowledge of the layout, or browse
  `docs/tool-catalog.md` rendered output.

## Parameters
_(none)_

## Returns
On success:
```
{
  ok: true,
  data: {
    tools: [
      {name, version, owner, classification, tags, domain, purpose},
      ...
    ],
    skills: [
      {name, version, description},
      ...
    ]
  }
}
```

## Errors
_(none — the tool always succeeds with the current state.)_

## Examples
### Inventory before scaffolding
Call: `repo.read_catalog()`
Returns: `{ok: true, data: {tools: [...], skills: [...]}}`

## See also
- `repo.search_catalog` — relevance-scored lookup, preferred for dedup checks.
- `repo.read_doc` — read raw markdown from `docs/`.

</details>

#### `repo.read_doc` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.read_doc
version: 1
owner: team-platform-ai
classification: [public]
tags: [docs, read, reference]
---

# repo.read_doc

## Purpose
Read a markdown file from the repository's `docs/` directory and return its
full contents.

## When to use
- A skill needs to consult the authoring guides at runtime (e.g. the
  skill_creator reads `authoring-tools.md` before guiding the user).
- The user asks "what does the authoring guide say about X" and the answer
  lives in `docs/`.

## When NOT to use
- For reading anything outside `docs/` — this tool refuses out-of-tree paths.
- For reading a skill's `references/*.md` — use `repo.read_doc` only against
  the top-level `docs/` directory; references are loaded by the framework
  itself when a skill activates.
- For reading the live tool/skill catalog data — use `repo.read_catalog`,
  which returns structured JSON, not raw markdown.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path relative to `docs/`, e.g. `"authoring-tools.md"` or `"example-kyc-screening.md"`. |

## Returns
On success: `{ok: true, data: {path: "docs/...", content: "<full markdown>"}}`

## Errors
- `path_outside_docs` — path attempts to escape `docs/`.
- `not_found` — no such file under `docs/`.

## Examples
### Read the tool-authoring guide
Call: `repo.read_doc(path="authoring-tools.md")`
Returns: `{ok: true, data: {path: "docs/authoring-tools.md", content: "# Authoring tools\n..."}}`

### Read the worked example
Call: `repo.read_doc(path="example-kyc-screening.md")`

## See also
- `repo.read_catalog` — structured tool/skill list, not raw markdown.
- `repo.search_catalog` — find tools by name/tag/description.

</details>

#### `repo.scaffold_pack` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

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
Call: `repo.scaffold_pack(name="credit_analyst", owner="team-credit-ai", description="Credit analysts drafting and reviewing corporate credit memos.", skills=["credit_memo", "xlsx_analysis"], classification="internal")`
Returns: `{ok: true, data: {pack: "credit_analyst", created: ["packs/credit_analyst.yaml"], next_steps: [...]}}`

## See also
- `repo.scaffold_skill` — create any missing skills first.
- `repo.scaffold_tool` — create any missing tools first.

</details>

#### `repo.scaffold_skill` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

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

</details>

#### `repo.scaffold_tool` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.scaffold_tool
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, tool-authoring]
---

# repo.scaffold_tool

## Purpose
Create the skeleton files for a new tool from the canonical template:
`registry.py`, `impl.py`, `cards/<verb>.md`, and a stub test file.

## When to use
- The skill_creator skill has confirmed (via `repo.search_catalog`) that the
  proposed tool does not duplicate an existing one, and the user has agreed
  on the name and owner.

## When NOT to use
- Before running a dedup check — always call `repo.search_catalog` first.
- To modify an existing tool — this tool only creates new artifacts and
  refuses overwrites.
- To create a tool in a domain you have not discussed with the user — the
  domain (`<domain>` in `<domain>.<verb>`) is a long-lived shared namespace
  and shouldn't be invented on the fly.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Full tool name as `<domain>.<verb>`, lowercase + underscores only. |
| owner | string | yes | Owning team, e.g. `"team-credit-ai"`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    tool: "<name>",
    created: ["tools/<domain>/", "tools/<domain>/cards/<verb>.md", ...],
    next_steps: [...]   # human-readable list of follow-ups
  }
}
```

## Errors
- `invalid_name` — name not `<domain>.<verb>` or contains invalid characters.
- `already_exists` — tool with that name is already registered, or the card
  file already exists.

## Examples
### First tool in a new domain
Call: `repo.scaffold_tool(name="email.send", owner="team-comms-ai")`
Returns: `{ok: true, data: {tool: "email.send", created: ["tools/email"], next_steps: [...]}}`

### Adding a new verb to an existing domain
Call: `repo.scaffold_tool(name="xlsx.add_chart", owner="team-doc-ai")`
Returns: `{ok: true, data: {tool: "xlsx.add_chart", created: ["tools/xlsx/cards/add_chart.md"], next_steps: [...]}}`

## See also
- `repo.search_catalog` — call first to confirm no duplicate.
- `repo.scaffold_skill` — for new skills.

</details>

#### `repo.search_catalog` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.search_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, search, dedup]
---

# repo.search_catalog

## Purpose
Search the live tool catalog by free-text query and return ranked hits with
their purpose lines, tags, and owners. Used primarily as a dedup check
before proposing a new tool.

## When to use
- Before scaffolding a new tool, search for near-duplicates the author may
  have missed.
- A skill author is picking tools for a workflow step and wants candidates.

## When NOT to use
- For listing every tool — use `repo.read_catalog`, which returns the full
  inventory without scoring.
- For reading the actual card body of a specific tool — fetch via the
  catalog entry name.

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | Free-text, e.g. `"read excel"`, `"summarize text"`, `"docstore"`. Lower-case match. |
| limit | int | no | Max hits returned, default 8, max 50. |

## Returns
On success:
```
{
  ok: true,
  data: {
    query: "<echoed>",
    hits: [
      {name, score, tags, purpose, owner},
      ...   # sorted by score desc
    ]
  }
}
```

## Errors
- `empty_query` — query is empty or whitespace-only.

## Examples
### Dedup check before adding `xlsx.read_sheet`
Call: `repo.search_catalog(query="read excel")`
Returns: `{ok: true, data: {query: "read excel", hits: [{name: "xlsx.read", score: 0.95, ...}, ...]}}`

### Browse summarization tools
Call: `repo.search_catalog(query="summarize", limit=5)`

## See also
- `repo.read_catalog` — full inventory, unranked.
- `repo.scaffold_tool` — call after confirming no duplicate exists.

</details>

### `text`

#### `text.extract_lines` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: text.extract_lines
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, extract, numeric, deterministic]
---

# text.extract_lines

## Purpose
Scan a text and return the subset of lines that contain numbers, percentages,
currency amounts, or `Key: value` patterns. Deterministic, no LLM. The
returned lines are the raw material a skill can summarize or cite.

## When to use
- A skill is processing a free-form document (credit input, KYC dossier,
  research note) and needs to surface the quantitative / structured lines.
- Before drafting a summary, to give the model a ranked candidate set of
  lines worth quoting verbatim.

## When NOT to use
- For producing a prose summary — the skill itself should do that using
  the lines this tool returns. There is no LLM-summarization tool by design.
- For parsing structured spreadsheets — use `xlsx.read`.
- For extracting tables out of a PDF — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to scan. |
| kinds | list[string] | no | Subset of `numeric`, `percentage`, `currency`, `key_value`. Default: all four. |

## Returns
On success:
```
{
  ok: true,
  data: {
    lines: [
      {line_no: 4, text: "Revenue: EUR 412m (+8.2% YoY)", kinds: ["numeric","percentage","currency","key_value"]},
      ...
    ],
    total_matched: 7
  }
}
```

## Errors
- `empty_input` — the text was empty or whitespace-only.

## Examples
### Surface numeric lines from a credit file
Call: `text.extract_lines(text="<credit file body>")`
Returns: `{ok: true, data: {lines: [{line_no: 4, text: "Revenue: EUR 412m ...", kinds: [...]}, ...], total_matched: 6}}`

### Only key:value lines
Call: `text.extract_lines(text="...", kinds=["key_value"])`

## See also
- `text.word_count` — basic metrics.
- `xlsx.read` — when the source is tabular, not prose.

</details>

#### `text.word_count` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: text.word_count
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, metrics, deterministic]
---

# text.word_count

## Purpose
Return the number of words and characters in a piece of text.

## When to use
- A skill needs to check whether a draft fits a length budget before
  returning it.
- Quick sanity check on a document's size before deciding whether to chunk it.

## When NOT to use
- For token counting against a specific model — this tool returns word
  count, not tokens.
- For extracting structured content — use `text.extract_lines`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to measure. |

## Returns
On success: `{ok: true, data: {words: <int>, chars: <int>}}`

## Errors
_(none)_

## Examples
### Measure a draft
Call: `text.word_count(text="...")`
Returns: `{ok: true, data: {words: 412, chars: 2890}}`

## See also
- `text.extract_lines` — for content-level extraction.

</details>

### `xlsx`

#### `xlsx.read` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, tabular]
---

# xlsx.read

## Purpose
Read a spreadsheet file (`.xlsx`, `.xlsm`, `.csv`, or `.tsv`) and return its
contents as a header row + list of data rows.

## When to use
- The user gives you a path to a spreadsheet and asks you to inspect, analyse,
  or summarise its contents.
- A skill needs the rows from a workbook before doing any analysis on them.

## When NOT to use
- For writing or modifying a workbook — not supported yet; will be `xlsx.write_*`.
- For complex pivot / chart inspection — not supported; returns raw cell values.
- For reading PDFs of spreadsheet exports — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Absolute or relative path to the file. |
| sheet | string | no | Sheet name (xlsx only). Defaults to the first sheet. |
| has_header | bool | no | If true (default), the first row becomes `headers`; otherwise it stays in `rows`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    sheet: "<name>",
    headers: ["col1", "col2", ...] | null,
    rows: [[v1, v2, ...], ...],
    row_count: <int>
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `sheet_not_found` — requested sheet name is not in the workbook.
- `dependency_missing` — openpyxl is not installed in this environment.

## Examples
### Read default sheet of an xlsx
Call: `xlsx.read(path="/data/loans.xlsx")`
Returns: `{ok: true, data: {sheet: "Sheet1", headers: ["id","amount"], rows: [["L1",100], ...], row_count: 20}}`

### Read a specific sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1")`

### Read a CSV
Call: `xlsx.read(path="/data/loans.csv")`

## See also
- `text.extract_lines` — for prose, not tabular sources.
- `docstore.fetch` — when the source is internally stored rather than at a path.

</details>

## By tag

- **catalog** — `repo.read_catalog`, `repo.search_catalog`
- **dedup** — `repo.search_catalog`
- **deterministic** — `text.extract_lines`, `text.word_count`
- **diagnostic** — `core.echo`
- **docs** — `repo.read_doc`
- **docstore** — `docstore.fetch`
- **extract** — `text.extract_lines`
- **fetch** — `docstore.fetch`
- **internal-docs** — `docstore.fetch`
- **metrics** — `text.word_count`
- **numeric** — `text.extract_lines`
- **pack-authoring** — `repo.scaffold_pack`
- **read** — `docstore.fetch`, `repo.read_catalog`, `repo.read_doc`, `xlsx.read`
- **reference** — `repo.read_catalog`, `repo.read_doc`
- **scaffold** — `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
- **search** — `repo.search_catalog`
- **skill-authoring** — `repo.scaffold_skill`
- **smoke-test** — `core.echo`
- **spreadsheet** — `xlsx.read`
- **tabular** — `xlsx.read`
- **text** — `text.extract_lines`, `text.word_count`
- **tool-authoring** — `repo.scaffold_tool`
- **write** — `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
