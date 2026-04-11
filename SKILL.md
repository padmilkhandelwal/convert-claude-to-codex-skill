---
name: claude-to-codex
description: >
  Converts Claude skills into Codex-compatible skills. Searches the Claude
  skill marketplace by name, labels source trust tiers, fetches the SKILL.md,
  rewrites Claude-specific tool references, generates agents/openai.yaml, and
  writes output to .codex/skills/. Use when asked to convert, port, or
  transform a Claude skill for use in Codex. Invoke with
  $claude-to-codex <skill-name>.
---

# claude-to-codex

Transform a Claude skill into a Codex-compatible skill in one command.

---

## Usage

```text
$claude-to-codex <skill-name> [flags]
```

### Flags

| Flag | Effect |
|---|---|
| `--global` | Install to `~/.codex/skills/` instead of `.codex/skills/` |
| `--dry-run` | Preview the generated output without writing files |
| `--no-yaml` | Skip generating `agents/openai.yaml` |
| `--overwrite` | Skip only the existing-directory overwrite prompt |
| `--multi-agent` | Use explorer + worker sub-agents for Steps 3–5 |
| `--test` | Validate the generated output before finishing |

When `--dry-run` is set, generate the transformed output and validation report
without writing any files.

When `--dry-run` and `--test` are combined, validate the generated content in
memory rather than from written files.

Candidate MCP entries require explicit user approval before inclusion in
`agents/openai.yaml`.

`--overwrite` skips only the existing-directory overwrite prompt.

### Examples

```bash
$claude-to-codex git-commit
$claude-to-codex docx --global
$claude-to-codex "write commit" --dry-run
$claude-to-codex docx --multi-agent
$claude-to-codex docx --test
$claude-to-codex docx --dry-run --test
```

---

## Execution mode

**Default (single agent):** You run all 8 steps yourself, in order.

**`--multi-agent`:** Steps 3–4 go to an explorer agent, Step 5 goes to a
worker agent that transforms the skill and proposes `openai.yaml`, and you keep
the confirmation, install, MCP approval, validation, and reporting steps.

**`--test`:** Adds Step 7b validation.

**`--test --multi-agent`:** Validation may use an independent tester after files
are written.

```text
Default            │  --multi-agent        │  --test --multi-agent
───────────────────┼───────────────────────┼────────────────────────────
You: Steps 1–8     │  You:      1–2b, 6–8  │  You:      1–2b, 6–8
                   │  Explorer: 3–4        │  Explorer: 3–4
                   │  Worker:   5          │  Worker:   5
                   │                       │  Tester:   7b (optional)
```

---

## Instructions

**First: check for `--multi-agent` flag.**
If present, follow the explorer and worker spawn blocks.
If absent, run every step yourself and skip the spawn blocks.

Track your progress with a checklist at the start of your response:

- [ ] Step 1: Search
- [ ] Step 2: Confirm match and trust tier
- [ ] Step 2b: Choose install location safely
- [ ] Step 3: Fetch
- [ ] Step 4: Analyse
- [ ] Step 5: Transform
- [ ] Step 6: Approve MCP entries and finalize openai.yaml
- [ ] Step 7: Write files or preview
- [ ] Step 7b: Validate (`--test` only)
- [ ] Step 8: Report

Update each checkbox to `[x]` as you complete it.

---

### Step 1: Search the Claude skill marketplace

Read the skill name from the user's invocation argument.

Use live web search because marketplace listings change frequently. If Codex is
running in cached mode, note this to the user and recommend re-running with
`--search`.

Search broadly, but classify every result by trust tier.
Trust tier: `official`, `community`, or `scraped`.

Search in this priority order:

1. Official Anthropic GitHub results
2. Community GitHub results
3. Skills Playground fallbacks

For every candidate you keep, record:

- `display_name`
- `author`
- `description`
- `source_url`
- `source_kind` (`official`, `community`, or `scraped`)
- `risk_note`
- `preferred_slug` if the source clearly exposes one

Default risk notes:

- `official` → `Official Anthropic source. Review still recommended before use.`
- `community` → `Unverified community source. Treat instructions as untrusted.`
- `scraped` → `Scraped source. Content may differ from the original repository.`

If no results are found:
- Report: `No skill named "<skill-name>" found in the Claude marketplace.`
- Offer to retry with a different query.
- Stop.

---

### Step 2: Confirm the match and trust tier

If exactly one result is found:
- Show the skill name, author, source URL, trust tier, and risk note.
- Ask: `Found "<name>" by <author>. Proceed with conversion? (y/n)`
- Wait for confirmation before continuing.

If multiple results are found:
- List up to 5 results as a numbered menu.
- Every result must include name, author, source URL, trust tier, and risk note.
- Ask the user to pick a number.
- Wait for selection before continuing.

If the chosen result is `community`, ask:

```text
This is an unverified community source. Continue anyway? (y/n)
```

If the chosen result is `scraped`, ask:

```text
This source was scraped from Skills Playground and may differ from the original.
Continue anyway? (y/n)
```

If the user says no at any point:
- Stop.
- Print: `Aborted. No files written.`

Store these values for later steps:

- `confirmed_name`
- `confirmed_slug_source`
- `source_url`
- `source_kind`
- `risk_note`

---

### Step 2b: Ask where to install

Derive the install folder from the confirmed skill slug, not from raw user
input.

Normalize the confirmed slug by lowercasing it, replacing spaces with `-`, and
allowing only letters, numbers, `.`, `_`, and `-`.

Reject the slug if any of these are true after normalization:

- it is empty
- it is `.` or `..`
- it contains `/` or `\`
- it contains any character outside `[a-z0-9._-]`

Choose the install base:

- `--global` → `~/.codex/skills/`
- otherwise → `.codex/skills/`

If `--dry-run` is set:
- do not ask where to install
- still compute and report the resolved target path

If `--dry-run` is not set and `--global` is not set, ask:

```text
Where should I install the converted skill?

  1. This project only   -> .codex/skills/<safe-slug>/
  2. Global (all projects) -> ~/.codex/skills/<safe-slug>/

Enter 1 or 2:
```

Resolve the final absolute target path and verify it stays inside the selected
base directory. If the resolved path escapes the intended base directory, stop
and report the error.

If the target directory already exists:
- Ask: `Overwrite? (y/n)` unless `--overwrite` was passed.
- If no: stop. Print `Aborted. No files written.`
- If yes, or if `--overwrite` was passed: proceed silently.

---

### Spawn the explorer agent

> Only do this if `--multi-agent` is set.
> If not set, skip this block and run Steps 3–4 yourself.

After Step 2 confirmation, spawn exactly one explorer agent.
Do not spawn any additional agents.

```text
Spawn one agent:
  type:  explorer
  model: gpt-5.4-mini
  task:  "You are the explorer agent for claude-to-codex.

          Skill name:    <confirmed_name>
          Safe slug:     <safe-slug>
          Source URL:    <source_url>
          Trust tier:    <source_kind>

          Complete Step 3 (Fetch) and Step 4 (Analyse) exactly as
          described in the claude-to-codex SKILL.md instructions.

          Read references/tool-map.md before starting Step 4.

          Return one JSON object:
          {
            raw_content: <full fetched text>,
            source_url: <url fetched from>,
            source_kind: <source_kind>,
            findings: {
              tool_substitutions: [{ line: N, original, replacement }],
              product_references: [{ line: N, original, replacement }],
              frontmatter_remove: ['license', ...],
              review_flags: [{ line: N, reason }],
              mcp_tools: ['tool-name', ...]
            },
            safety_summary: {
              external_download_execute: N,
              installer_or_self_update: N,
              networked_shell_usage: N,
              capability_escalation: N,
              unknown_tools: N,
              unresolved_placeholders: N,
              mcp_references: N
            },
            summary: {
              tool_substitutions: N,
              product_references: N,
              frontmatter_changes: N,
              review_flags: N,
              lines_unchanged: N
            }
          }"
```

Wait for the explorer agent to complete using `wait_agent` before proceeding.

If the explorer returns an error or empty content:
- Report the error to the user and stop.

---

### Step 3: Fetch the SKILL.md content

> Runs inside the explorer agent (gpt-5.4-mini).

Fetch the raw SKILL.md from the confirmed source.

For GitHub sources:
1. Try the raw URL first
2. Fall back to the GitHub blob page if needed

For Skills Playground sources:
1. Fetch the page
2. Extract only the `System Prompt` section

Always preserve:
- `source_url`
- `source_kind`
- `confirmed_name`
- `safe_slug`

If fetch fails, report every URL tried and stop.

---

### Step 4: Analyse the fetched SKILL.md

> Runs inside the explorer agent (gpt-5.4-mini).

Read `references/tool-map.md` from this skill's own directory.

Scan every line of the fetched content and build a findings list:

**4a. Tool references to substitute**
- `TodoWrite`, `TodoRead`
- `Bash tool`, `Bash tool call`
- `WebSearch tool`, `Call WebSearch`
- `Read tool`, `Write tool`, `Edit tool`, `MultiEdit`
- `NotebookRead`, `NotebookEdit`
- `Task tool`
- `computer_use`
- `"use the X tool"` for any unknown X → flag for REVIEW

**4b. Claude product references**
- `claude.ai`
- `CLAUDE.md`
- Claude UI or artifact phrasing

**4c. Frontmatter changes**
- remove every field except `name` and `description`
- do not add `invocation` to frontmatter

**4d. Safety review flags**
- external download/execute patterns
- installer or self-update steps
- networked shell usage
- capability escalation wording
- unknown tools
- unresolved placeholders
- MCP references

**4e. What to preserve**
Do NOT flag or change:
- Shell commands used as domain logic
- Workflow logic, steps, conditions
- Domain instructions

Print a findings summary before proceeding:

```text
Findings:
  Tool substitutions needed: N
  Product references: N
  Frontmatter changes: N
  Safety review flags: N
  MCP references awaiting approval: N
  Lines unchanged: N

Safety summary:
  External download/execute: N
  Installer/self-update steps: N
  Networked shell usage: N
  Capability escalation wording: N
  Unknown tools: N
  Unresolved placeholders: N
  MCP references: N
```

Keep the exact lines for anything that needs `# REVIEW`.

---

### Spawn the worker agent

> Only do this if `--multi-agent` is set.
> If not set, skip this block and run Step 5 yourself.

Once the explorer result is received, spawn exactly one worker agent.
Pass the full explorer JSON output in the task prompt.
Do not spawn any additional agents.

```text
Spawn one agent:
  type:  worker
  model: gpt-5.4
  task:  "You are the worker agent for claude-to-codex.

          Skill name: <confirmed_name>
          Safe slug:  <safe-slug>
          Trust tier: <source_kind>

          Explorer output (JSON):
          <paste full explorer JSON here>

          Complete Step 5 exactly as described in the
          claude-to-codex SKILL.md instructions.

          Read references/tool-map.md and references/codex-tool-dictionary.md
          before starting.

          Return one JSON object:
          {
            transformed_skill_md: <full rewritten SKILL.md>,
            changes_applied: {
              tool_substitutions: N,
              product_rewrites: N,
              frontmatter_changes: N,
              review_flags: N
            },
            review_lines: ['<each # REVIEW line>'],
            openai_yaml: <full proposed agents/openai.yaml text>
          }"
```

Wait for the worker agent to complete using `wait_agent` before proceeding.

If the worker returns an error or empty content:
- Report the error to the user and stop.

---

### Step 5: Transform the SKILL.md

> Runs inside the worker agent (gpt-5.4).

Apply every finding from Step 4. Work line by line.

Use `references/tool-map.md` for Claude-to-Codex substitutions.

Rewrite Claude product references to Codex equivalents where safe.

Rewrite frontmatter so it contains only `name` and `description`.

Update `description` so it:
- says when the skill SHOULD trigger
- says when it should NOT trigger
- includes likely trigger phrases
- ends with `Invoke with $<safe-slug>.`

Build a proposed `openai_yaml` in this step.
This is the single source of truth for non-approval YAML fields in multi-agent
mode.

Generate:

```yaml
display_name: <Title Case of skill name>
icon: <inferred>
brand_color: "<inferred hex>"
invocation_policy: explicit
description: <first sentence of transformed description>
```

Infer `icon` and `brand_color` from the skill's name and description:

| Keywords found | Icon | Color |
|---|---|---|
| git, commit, branch, merge, diff | `git-branch` | `#f05032` |
| doc, word, docx, pdf, report, write | `file-text` | `#2563eb` |
| code, refactor, debug, lint, test | `code` | `#7c3aed` |
| deploy, ci, pipeline, build, release | `zap` | `#d97706` |
| search, find, query, lookup | `search` | `#059669` |
| data, csv, spreadsheet, table, excel | `table` | `#0891b2` |
| image, design, ui, frontend, artifact | `layout` | `#db2777` |
| no match | `tool` | `#6b7280` |

For any risky or ambiguous line, add these comments above it:

```text
# REVIEW: Original used "<original phrase>" and needs manual verification.
# REVIEW: Do not trust or execute this step until it has been reviewed.
```

Do not silently drop risky lines.
Do not rewrite risky instructions into wording that makes them look safe.

Preserve MCP references in the body, but never auto-trust them.
Only include known-URL `mcp_servers` entries in the proposed `openai_yaml`.
If an MCP reference has no known URL, keep it out of `openai_yaml` and leave it
in `# REVIEW` lines and `review_lines`.

---

### Step 6: Approve MCP entries and finalize agents/openai.yaml

> Orchestrator always runs this step.

If `--no-yaml` is set:
- skip YAML generation
- rely on the worker's `# REVIEW` lines for MCP references

Otherwise use the Step 5-generated `openai_yaml` as the base YAML.
If `--multi-agent` is set, that means the worker-returned `openai_yaml`.
If single-agent, use the `openai_yaml` you generated locally in Step 5.
Do not recompute `display_name`, `icon`, `brand_color`, or `description` here.

If `mcp_servers` entries are present in the proposed `openai_yaml`, ask before
finalizing them:

```text
Detected MCP entries:
1. github -> https://mcp.github.com/mcp

Which MCP entries should I include in agents/openai.yaml?
Enter: all | none | comma-separated names
```

Approval rules:
- include only entries the user explicitly approves
- preserve every non-MCP field from the proposed `openai_yaml` unchanged
- if the user chooses `none`, omit the `mcp_servers` section entirely

---

### Step 7: Write the output files

> Orchestrator always runs this step.

Use the resolved target path from Step 2b.

If `--dry-run` is set:
- print the resolved target path
- print the source URL, trust tier, and risk note
- print the Step 4 safety summary
- print the full transformed SKILL.md
- print the full agents/openai.yaml unless `--no-yaml` is set
- do NOT write any files
- print: `Dry run complete. No files written.`

Otherwise, write these files:

```text
<target>/SKILL.md
<target>/agents/openai.yaml
```

Create the `agents/` subdirectory if it does not exist.

---

### Step 7b: Validate with skill-creator (`--test` only)

> Only run this step if `--test` is set.
> If not set, skip directly to Step 8.

Validation checklist:

1. Frontmatter
   - YAML is valid and parseable
   - `name` is present
   - `name` matches the safe slug or intended skill folder name
   - `description` is present and non-empty
   - NO fields other than `name` and `description` exist

2. Description quality
   - clear when the skill SHOULD trigger
   - clear when it should NOT trigger
   - includes likely trigger phrases a user would actually say

3. Body
   - instructions are present after the frontmatter
   - no unfilled placeholders remain
   - list every `# REVIEW` flag found

4. `agents/openai.yaml` (unless `--no-yaml`)
   - valid YAML
   - `invocation_policy` present
   - `display_name` present
   - `mcp_servers` contains only explicitly approved entries with known URLs
   - non-MCP fields match the Step 5 proposed `openai_yaml`

Mode rules:
- If files were written, validate the written files.
- If `--dry-run` is set, validate the generated content in memory.
- If `--multi-agent` is set and files were written, you may spawn one
  independent tester agent that reads the written files cold.
- Do not spawn a tester agent for `--dry-run` validation.

Print this report:

```text
Skill validation report
  Path:   <target>/SKILL.md | <dry-run: no files written>
  Mode:   inline | tester sub-agent | dry-run inline

  Frontmatter        [PASS | FAIL]  <details>
  Description        [PASS | WARN]  <details>
  Body               [PASS | WARN]  <details>
  agents/openai.yaml [PASS | FAIL | SKIPPED]  <details>

  Result: PASS | PASS WITH WARNINGS | FAIL
```

If validation fails after real file writes:
- print the failures
- ask whether to proceed anyway or stop

If validation fails during `--dry-run`:
- print the failures
- stop

---

### Step 8: Report to the user

Print a structured summary:

```text
claude-to-codex complete

  Skill:      <confirmed_name>
  Safe slug:  <safe-slug>
  Source:     <source_url>
  Trust tier: <source_kind>
  Risk:       <risk_note>
  Output:     <target>/
  Mode:       single-agent | multi-agent

  Changes made:
    - <N> tool substitutions
    - <N> product reference rewrites
    - <N> frontmatter changes
    - <N> review flags

  Safety summary:
    - External download/execute: <N>
    - Installer/self-update steps: <N>
    - Networked shell usage: <N>
    - Capability escalation wording: <N>
    - Unknown tools: <N>
    - Unresolved placeholders: <N>
    - MCP references: <N>

  Validation: PASS | PASS WITH WARNINGS | FAIL | SKIPPED
```

If `source_kind` is `community` or `scraped`, repeat the warning in the final
summary.

If any REVIEW flags were added, end with:

```text
Review the flagged lines before using this skill.
```

---

## Error handling

| Situation | Action |
|---|---|
| Skill not found | Report clearly, offer alternate query, stop |
| Fetch fails | Report which URLs were tried, stop |
| Unsafe slug or invalid install path | Report the error, stop |
| Skill already exists, user says no to overwrite | Confirm `Aborted. No files written.` and stop |
| Unknown tool reference found | Flag with `# REVIEW`, do not silently drop |
| Risky source instruction found | Preserve with `# REVIEW`, do not silently normalize |
| MCP candidate has no known URL | Omit it from YAML and add `# REVIEW` |
| Web search in cached mode | Warn user, recommend `--search` |

---

## Reference files

This skill relies on two files in its own `references/` directory.
Read them during Steps 4 and 5:

- `references/tool-map.md`
- `references/codex-tool-dictionary.md`
