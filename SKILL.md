---
name: claude-to-codex
description: >
  Converts any Claude skill into a Codex-compatible skill. Searches the
  Claude skill marketplace by name, fetches the SKILL.md, rewrites
  Claude-specific tool references, generates agents/openai.yaml, and
  writes output to .codex/skills/. Use when asked to convert, port, or
  transform a Claude skill for use in Codex. Invoke with
  $claude-to-codex <skill-name>.
---

# claude-to-codex

Transform any Claude skill into a Codex-compatible skill in one command.

---

## Usage

```
$claude-to-codex <skill-name> [flags]
```

### Flags

| Flag | Effect |
|---|---|
| `--global` | Install to `~/.codex/skills/` instead of `.codex/skills/` |
| `--dry-run` | Print the transformed SKILL.md without writing any files |
| `--no-yaml` | Skip generating `agents/openai.yaml` |
| `--overwrite` | Replace an existing skill without prompting |
| `--multi-agent` | Use explorer + worker sub-agents for Steps 3–6 (see below) |
| `--test` | After writing files, run skill-creator validation on the output |

### Examples

```bash
$claude-to-codex git-commit
$claude-to-codex docx --global
$claude-to-codex "write commit" --dry-run
$claude-to-codex docx --multi-agent
$claude-to-codex docx --test              # convert + validate output
$claude-to-codex docx --dry-run --test    # preview + validate without writing
```

---

## Execution mode

**Default (single agent):** You run all 8 steps yourself, in order.
Fast, simple, best for most single conversions.

**`--multi-agent`:** Steps 3–4 go to an explorer agent, Steps 5–6 to a
worker agent. Use for large skills (500+ lines) or bulk conversions.

**`--test`:** Adds Step 7b validation after writing. Inline by default.

**`--test --multi-agent`:** Step 7b spawns an independent tester sub-agent
that reads the output cold — no context of how it was written. Strictest
validation mode.

```
Default            │  --multi-agent        │  --test --multi-agent
───────────────────┼───────────────────────┼────────────────────────────
You: Steps 1–8     │  You:      1–2, 7–8   │  You:      1–2, 7–8
                   │  Explorer: 3–4        │  Explorer: 3–4
                   │  Worker:   5–6        │  Worker:   5–6
                   │                       │  Tester:   7b (cold read)
```

---

## Instructions

**First: check for `--multi-agent` flag.**
If present, follow the sub-agent spawn blocks when you reach Steps 3 and 5.
If absent, run all steps yourself — skip all spawn blocks entirely.

Track your progress with a checklist at the start of your response:

- [ ] Step 1: Search
- [ ] Step 2: Confirm match
- [ ] Step 2b: Choose install location
- [ ] Step 3: Fetch
- [ ] Step 4: Analyse
- [ ] Step 5: Transform
- [ ] Step 6: Generate openai.yaml
- [ ] Step 7: Write files
- [ ] Step 7b: Validate (--test only)
- [ ] Step 8: Report

Update each checkbox to [x] as you complete it.

---

### Step 1: Search the Claude skill marketplace

Read the skill name from the user's invocation argument.

Search for the skill using the following sources in priority order:

1. `site:github.com/anthropics/skills <skill-name>`
2. `site:skillsplayground.com <skill-name> claude skill`
3. `<skill-name> claude SKILL.md site:github.com`

Use live web search (`--search` mode) because marketplace listings change
frequently. If Codex is running in cached mode, note this to the user and
recommend re-running with `--search`.

If no results are found:
- Report: "No skill named `<skill-name>` found in the Claude marketplace."
- Offer to retry with a different query.
- Stop.

---

### Step 2: Confirm the match

If exactly one result is found:
- Show the skill name, author, and one-line description.
- Ask: "Found `<name>` by <author>. Proceed with conversion? (y/n)"
- Wait for confirmation before continuing.

If multiple results are found:
- List up to 5 results as a numbered menu (name + author + description).
- Ask the user to pick a number.
- Wait for selection before continuing.

---

### Step 2b: Ask where to install

> Skip this step if `--global` or `--dry-run` was already passed.
> `--global` flag → use `~/.codex/skills/<sanitized-name>/` and proceed.
> `--dry-run` flag → no install location needed, proceed.

**Sanitize the skill name:**
Before constructing any paths, create `<sanitized-name>` from `<skill-name>`:
1. Replace all spaces with hyphens.
2. Remove any characters that are not alphanumeric, hyphens, or underscores.
3. This prevents path traversal (by removing `.` and `/`) and ensures a valid directory name.

Ask the user:

```
Where should I install the converted skill?

  1. This project only   →  .codex/skills/<sanitized-name>/
  2. Global (all projects)  →  ~/.codex/skills/<sanitized-name>/

Enter 1 or 2:
```

Wait for their answer. Store the chosen path as the target for Step 7.

If they pick 1: target = `.codex/skills/<sanitized-name>/`
If they pick 2: target = `~/.codex/skills/<sanitized-name>/`

If the target directory already exists:
- Tell them: "`<target>` already exists."
- Ask: "Overwrite? (y/n)"
- If no: stop. Print "Aborted. No files written."
- If yes, or if `--overwrite` was passed: proceed silently.

---

### Spawn the explorer agent

> Only do this if `--multi-agent` flag is set.
> If not set, skip this block and run Steps 3–4 yourself.

After Step 2 confirmation, spawn exactly one explorer agent.
Do not spawn any additional agents at this point.

```
Spawn one agent:
  type:  explorer
  model: gpt-5.4-mini
  task:  "You are the explorer agent for claude-to-codex.

          Skill name:    <skill-name>
          Confirmed URL: <url-from-step-2>

          Complete Step 3 (Fetch) and Step 4 (Analyse) exactly as
          described in the claude-to-codex SKILL.md instructions.

          Read references/tool-map.md before starting Step 4.

          Return your output as a single JSON object with this shape:
          {
            raw_content: <full text of the fetched SKILL.md>,
            source_url:  <url successfully fetched from>,
            findings: {
              tool_substitutions: [{ line: N, original, replacement }],
              product_references: [{ line: N, original, replacement }],
              frontmatter_remove: ['license', ...],
              review_flags:       [{ line: N, reason }],
              mcp_tools:          ['tool-name', ...]
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

If the explorer returns an error (fetch failed, content empty):
- Report the error to the user and stop.

---

### Step 3: Fetch the SKILL.md content

> Runs inside the explorer agent (gpt-5.4-mini).

Fetch the raw SKILL.md from the confirmed source. Try in this order:

1. Raw GitHub URL:
   `https://raw.githubusercontent.com/anthropics/skills/main/skills/<name>/SKILL.md`
2. GitHub blob page (parse raw content from HTML):
   `https://github.com/anthropics/skills/blob/main/skills/<name>/SKILL.md`
3. Skills Playground page:
   `https://skillsplayground.com/skills/<author>-skills-<name>/`
   Extract the "System Prompt" section.

Store the full raw content. If all three fail, report the error and stop.

---

### Step 4: Analyse the fetched SKILL.md

> Runs inside the explorer agent (gpt-5.4-mini).

Read `references/tool-map.md` from this skill's own directory.

Scan every line of the fetched content and build a findings list:

**4a. Tool references to substitute**
Look for any of these Claude-specific phrases:
- `TodoWrite`, `TodoRead`
- `Bash tool`, `Bash tool call`
- `WebSearch tool`, `Call WebSearch`
- `Read tool`, `Write tool`, `Edit tool`, `MultiEdit`
- `NotebookRead`, `NotebookEdit`
- `Task tool` (sub-agent delegation)
- `computer_use`
- `"use the X tool"` for any unknown X → flag for REVIEW

**4b. Claude product references**
- `claude.ai` (product UI)
- `CLAUDE.md` (Claude-specific config)
- `artifact` in the context of Claude's UI output panel
- `share in conversation` or similar Claude chat UI phrasing

**4c. Frontmatter fields to remove**
- `license`
- `model`
- `version`
- `author_url`

**4d. What to preserve**
Do NOT flag or change:
- Shell commands (grep, sed, git, npm, etc.)
- Workflow logic, steps, conditions
- Domain instructions (file formats, API calls, etc.)
- MCP tool names → preserve + add to openai.yaml
- Any line with "bash" used generically (not as a tool name)

Print a findings summary before proceeding:
```
Findings:
  Tool substitutions needed: N
  Product references: N
  Frontmatter changes: N
  Lines flagged for REVIEW: N
  Lines unchanged: N
```

---

### Spawn the worker agent

> Only do this if `--multi-agent` flag is set.
> If not set, skip this block and run Steps 5–6 yourself.

Once the explorer agent result is received, spawn exactly one worker agent.
Pass the full explorer JSON output in the task prompt.
Do not spawn any additional agents.

```
Spawn one agent:
  type:  worker
  model: gpt-5.4
  task:  "You are the worker agent for claude-to-codex.

          Skill name: <skill-name>

          Explorer output (JSON):
          <paste full explorer JSON here>

          Complete Step 5 (Transform) and Step 6 (Generate openai.yaml)
          exactly as described in the claude-to-codex SKILL.md instructions.

          Read references/tool-map.md and references/codex-tool-dictionary.md
          before starting Step 5.

          Return your output as a single JSON object with this shape:
          {
            transformed_skill_md: <full text of the rewritten SKILL.md>,
            openai_yaml:          <full text of agents/openai.yaml>,
            changes_applied: {
              tool_substitutions: N,
              product_rewrites:   N,
              frontmatter:        ['added invocation', 'removed license', ...],
              review_flags:       N
            }
          }"
```

Wait for the worker agent to complete using `wait_agent` before proceeding.

If the worker returns an error or empty content:
- Report the error to the user and stop.

---

### Step 5: Transform the SKILL.md

> Runs inside the worker agent (gpt-5.4).

Apply every finding from Step 4. Work line by line.

**5a. Tool substitutions**

Apply substitutions from `references/tool-map.md`:

| Claude | Codex |
|---|---|
| `Use TodoWrite to create a task list` | `Track your progress with a checklist in your response` |
| `Use TodoWrite to mark X as complete` | `Update your checklist to mark X as done` |
| `Use TodoRead to check remaining tasks` | `Review your checklist` |
| `Use the Bash tool to run <cmd>` | `Run <cmd> in the shell` |
| `Call Bash with command: <cmd>` | `Execute: <cmd>` |
| `Use the WebSearch tool to find...` | `Search the web for...` |
| `Call WebSearch with query: X` | `Search for X` |
| `Use the Read tool to open <file>` | `Read the contents of <file>` |
| `Use the Write tool to save to <file>` | `Write the output to <file>` |
| `Use the Edit tool` | `Edit the file` |
| `Use MultiEdit to apply changes` | `Apply all changes to the file` |
| `Use NotebookRead` | `Read the .ipynb file as JSON` |
| `Use NotebookEdit` | `Edit the cell in the notebook JSON` |
| `Use the Task tool to delegate X` | `Spawn one agent with task: "X". Do not spawn any additional agents.` |

**5b. Product reference rewrites**

| Claude phrasing | Codex phrasing |
|---|---|
| `claude.ai artifact` / `claude.ai HTML artifact` | `standalone HTML artifact` |
| `share the file in conversation so they can view it as an artifact` | `output the file path for the user` |
| `CLAUDE.md` | `AGENTS.md` |
| References to "Skills" as a Claude Code concept | Remove or rewrite as "Codex skills" |

**5c. Frontmatter rewrite**

Remove ALL fields except `name` and `description`. Per Codex skill-creator
spec, these are the ONLY valid frontmatter fields:

Remove: `license`, `model`, `version`, `author_url`, `invocation`

The `invocation_policy` field belongs in `agents/openai.yaml` — not frontmatter.

Update `description` to:
- Be clear about when the skill SHOULD trigger
- Include likely trigger phrases a user would actually say
- Note when it should NOT trigger (important for implicit matching)
- Append: `Invoke with $<skill-name>.`

**5d. Lines that need REVIEW**

For any line you cannot confidently rewrite, add a comment above it:
```
# REVIEW: Original used "<original phrase>" — no Codex equivalent found.
# Verify this step manually before using the skill.
```

Do not silently drop uncertain lines. Flag and preserve them.

---

### Step 6: Generate agents/openai.yaml

> Runs inside the worker agent (gpt-5.4).

Infer values from the skill's name and description using this logic:

**icon** — scan the description for keywords:

| Keywords found | Icon |
|---|---|
| git, commit, branch, merge, diff | `git-branch` |
| doc, word, docx, pdf, report, write | `file-text` |
| code, refactor, debug, lint, test | `code` |
| deploy, ci, pipeline, build, release | `zap` |
| search, find, query, lookup | `search` |
| data, csv, spreadsheet, table, excel | `table` |
| image, design, ui, frontend, artifact | `layout` |
| (no match) | `tool` |

**brand_color** — infer from icon:

| Icon | Color |
|---|---|
| `git-branch` | `#f05032` |
| `code` | `#7c3aed` |
| `file-text` | `#2563eb` |
| `zap` | `#d97706` |
| `search` | `#059669` |
| `table` | `#0891b2` |
| `layout` | `#db2777` |
| `tool` | `#6b7280` |

**Output:**

```yaml
display_name: <Title Case of skill name>
icon: <inferred>
brand_color: "<inferred hex>"
invocation_policy: explicit
description: <first sentence of transformed description>
```

If the skill references any MCP tools, add:

```yaml
mcp_servers:
  - name: <tool-name>
    url: <mcp-url-if-known>
```

---

### Step 7: Write the output files

> Orchestrator always runs this step.
> If `--multi-agent`: use the worker agent's returned JSON as file contents.
> If single-agent: use your own output from Steps 5–6.

Use the target path confirmed in Step 2b.
Location and overwrite decisions are already settled — do not ask again.

If `--dry-run` is set:
- Print the full transformed SKILL.md to the terminal.
- Print the full agents/openai.yaml to the terminal.
- Do NOT write any files.
- Print: "Dry run complete. No files written."
- Stop here.

Otherwise, write these files:

```
<target>/SKILL.md               ← transformed skill content
<target>/agents/openai.yaml     ← generated metadata (unless --no-yaml)
```

Create the `agents/` subdirectory if it does not exist.

---

### Step 7b: Validate with skill-creator (--test only)

> Only run this step if `--test` flag is set.
> If not set, skip directly to Step 8.

Two modes depending on whether `--multi-agent` is also set:

---

#### Mode A — inline validation (--test, no --multi-agent)

You run the validation yourself immediately after writing the files.
Read the output SKILL.md and agents/openai.yaml and check every item below.

**Validation checklist:**

1. Frontmatter
   - YAML is valid and parseable
   - `name` present and matches the skill folder name
   - `description` present and non-empty
   - NO fields other than `name` and `description` exist
     (invocation, license, model, version, author_url are all invalid)

2. Description quality
   - Clear when this skill SHOULD trigger
   - Clear when it should NOT trigger
   - Includes likely trigger phrases a user would actually say
   - Specific enough to avoid false implicit matches

3. Body
   - Instructions present after frontmatter
   - No unfilled placeholders (e.g. `<skill-name>` still literally in body)
   - List every `# REVIEW` flag found

4. agents/openai.yaml (unless --no-yaml)
   - Valid YAML
   - `invocation_policy` present
   - `display_name` present

---

#### Mode B — tester sub-agent (--test + --multi-agent)

Spawn exactly one tester agent. Do not spawn any additional agents.
Pass the output file paths only — not the content, not your analysis.
The tester must read the files cold, with no context of how they were built.
That independence is the whole point.

```
Spawn one agent:
  type:  explorer
  model: gpt-5.4-mini
  task:  "You are an independent skill validator for codex-stack.

          Read these files cold — you have no context of how they
          were written. That independence is essential.

          Files to validate:
            SKILL.md:          <target>/SKILL.md
            agents/openai.yaml: <target>/agents/openai.yaml
              (may not exist if --no-yaml was set)

          Validate every item in this checklist:

          FRONTMATTER (read the raw YAML block between --- markers)
          [ ] name field present
          [ ] name matches the folder name: <sanitized-name>
          [ ] description field present and non-empty
          [ ] NO extra fields exist (invocation, license, model,
              version, author_url are all invalid in frontmatter)
          [ ] YAML is parseable without errors

          DESCRIPTION QUALITY
          [ ] Clear when this skill SHOULD trigger
          [ ] Clear when it should NOT trigger
          [ ] Includes at least one trigger phrase a user would say
          [ ] Specific enough to avoid false implicit matches

          BODY
          [ ] Instructions are present after the frontmatter
          [ ] No unfilled placeholders — search for literal angle-bracket
              tokens like <skill-name>, <url>, <n> still in the body
          [ ] Count and list every line containing # REVIEW

          AGENTS/OPENAI.YAML (skip section if file does not exist)
          [ ] Valid YAML
          [ ] invocation_policy field present
          [ ] display_name field present

          Return your result as a single JSON object:
          {
            frontmatter: {
              pass: true/false,
              failures: ['<description of each failure>'],
              warnings: ['<description of each warning>']
            },
            description_quality: {
              pass: true/false,
              failures: [],
              warnings: []
            },
            body: {
              pass: true/false,
              failures: [],
              warnings: [],
              review_flags: ['<each # REVIEW line verbatim>']
            },
            openai_yaml: {
              pass: true/false,
              skipped: true/false,
              failures: [],
              warnings: []
            },
            overall: 'PASS' | 'PASS_WITH_WARNINGS' | 'FAIL',
            summary: '<one sentence>'
          }"
```

Wait for the tester agent to complete using `wait_agent`.

If the tester returns FAIL:
- Print the full validation report.
- Do NOT proceed to Step 8.
- Ask the user: "Validation failed. Fix the issues and re-run, or
  proceed anyway? (fix / proceed)"
- Wait for answer before continuing.

If the tester returns PASS or PASS_WITH_WARNINGS:
- Proceed to Step 8.
- Include the validation report in the Step 8 summary.

---

**Shared output format** (both modes print this in Step 8):

```
Skill validation report
  Path:   <target>/SKILL.md
  Mode:   inline | tester sub-agent

  Frontmatter        [PASS | FAIL]  <failures if any>
  Description        [PASS | WARN]  <warnings if any>
  Body               [PASS | WARN]  <# REVIEW count, placeholders>
  agents/openai.yaml [PASS | FAIL | SKIPPED]

  Result: PASS | PASS WITH WARNINGS | FAIL
```

---

### Step 8: Report to the user

Print a structured summary:

```
✓ claude-to-codex complete

  Skill:    <original-name>
  Source:   <url-fetched-from>
  Output:   <target-path>/
  Mode:     single-agent | multi-agent

  [If --multi-agent]:
  Agents used:
    Explorer (gpt-5.4-mini)  — fetch + analyse
    Worker   (gpt-5.4)       — transform + generate yaml

  Changes made:
    • <N> tool substitutions
    • <N> product reference rewrites
    • Frontmatter: added invocation_policy to openai.yaml, removed <fields>
    • agents/openai.yaml generated

  [If --test]:
  Validation: PASS | PASS WITH WARNINGS | FAIL
    <include full validation report here>

  Lines flagged for REVIEW: <N>
  <list each flagged line if N > 0>

  Next step:
    Test with: codex "$<skill-name> <example-input>"
```

If any REVIEW flags were added, end with:
```
  ⚠ Review flagged lines in <target>/SKILL.md before using.
```

---

## Error handling

| Situation | Action |
|---|---|
| Skill not found | Report clearly, offer alternate search query, stop |
| Fetch fails (all 3 sources) | Report which URLs were tried, stop |
| Target path is not writable | Report the permission error, suggest `--global` |
| Skill already exists, user says no to overwrite | Confirm "Aborted. No files written." and stop |
| Unknown tool reference found | Flag with `# REVIEW`, do not silently drop |
| Web search in cached mode | Warn user, recommend `--search` flag for fresh results |

---

## Reference files

This skill relies on two files in its own `references/` directory.
Read them during Steps 4 and 5:

- `references/tool-map.md` — Claude-specific tool phrases and their Codex rewrites
- `references/codex-tool-dictionary.md` — Full Codex tool reference including sub-agent patterns
