# claude-to-codex

> Convert any Claude skill into a ready-to-use Codex skill — automatically.
> Search by name, fetch, transform, validate, and install in one command.

---

## Why this exists

Claude and Codex skills share the same folder + Markdown structure, but differ
in ways that silently break compatibility:

| | Claude Code | Codex CLI |
|---|---|---|
| Task tracking | `TodoWrite`, `TodoRead` | Checklist in response |
| Shell execution | `Bash tool` | Shell directly |
| Web search | `WebSearch tool` | `Search the web for...` |
| File operations | `Read`, `Write`, `Edit` tools | Shell commands |
| Sub-agents | `Task tool` | `spawn_agent` (explicit prompt) |
| Config file | `CLAUDE.md` | `AGENTS.md` |
| App metadata | Not required | `agents/openai.yaml` |
| Frontmatter fields | name, description, license, model… | name + description only |

`$claude-to-codex` handles every substitution automatically, rewrites
frontmatter, generates `agents/openai.yaml`, optionally validates the output
with an independent tester agent, and writes the result directly to
`.codex/skills/` — zero manual editing required.

---

## How it works

```mermaid
flowchart LR
    A(["$claude-to-codex\ndocx --test"])

    A --> B["1 Search\nmarketplace"]
    B --> C["2 Confirm\nmatch"]
    C --> D["3 Fetch\nSKILL.md"]
    D --> E["4 Analyse\nClaude refs"]
    E --> F["5 Transform\nline by line"]
    F --> G["6 Generate\nopenai.yaml"]
    G --> H["7 Write\nto .codex/skills/"]
    H --> I["7b Validate\nskill-creator rules"]
    I --> J(["8 Report\nsummary"])

    style A fill:#e1f5ee,stroke:#0f6e56,color:#085041
    style J fill:#e1f5ee,stroke:#0f6e56,color:#085041
    style I fill:#faeeda,stroke:#854f0b,color:#633806
```

The `--test` step (7b) is optional. Without it, the skill goes straight from
write → report.

---

## Quick start

```bash
# 1. Clone and install globally
git clone https://github.com/<you>/claude-to-codex.git
mkdir -p ~/.codex/skills/claude-to-codex
cp -r claude-to-codex/. ~/.codex/skills/claude-to-codex/

# 2. Open Codex with live search (needed for marketplace lookups)
codex --search

# 3. Convert your first skill
$claude-to-codex docx
```

The skill will ask two questions before touching anything:
1. **Confirm the match** — shows name, author, description before proceeding
2. **Where to install** — project-local or global (skip with `--global` flag)

---

## Usage

```
$claude-to-codex <skill-name> [flags]
```

### Flags

| Flag | Description |
|---|---|
| `--global` | Install to `~/.codex/skills/` instead of `.codex/skills/` |
| `--dry-run` | Preview the transformed SKILL.md without writing files |
| `--no-yaml` | Skip generating `agents/openai.yaml` |
| `--overwrite` | Replace an existing skill without prompting |
| `--multi-agent` | Explorer + worker sub-agents for Steps 3–6 |
| `--test` | Validate output against skill-creator rules after writing |

---

## Examples

### Basic conversion

```bash
$claude-to-codex docx
```

The skill asks two questions before touching anything:

```
Found `docx` by anthropics. Generate and manage Word documents (.docx).
Proceed with conversion? (y/n): y

Where should I install the converted skill?

  1. This project only   →  .codex/skills/docx/
  2. Global (all projects)  →  ~/.codex/skills/docx/

Enter 1 or 2: 1

✓ Written to .codex/skills/docx/
```

Takes about 20 seconds end to end.

---

### Preview before committing

```bash
$claude-to-codex pptx --dry-run
```

Prints the transformed `SKILL.md` and `agents/openai.yaml` to the terminal
without writing any files. Use this to review changes before installing.

**Example output:**

```
--- SKILL.md (transformed) ---

---
name: pptx
description: >
  Create, edit, and format PowerPoint presentations (.pptx files).
  Use when asked to make slides, build a deck, or edit a presentation.
  Not for PDF or Word documents. Invoke with $pptx.
---

# pptx

To build a polished PowerPoint presentation, follow these steps:
...

--- agents/openai.yaml ---

display_name: PPTX Builder
icon: layout
brand_color: "#db2777"
invocation_policy: explicit
description: Create and edit PowerPoint presentations.

Dry run complete. No files written.
```

---

### Install globally for all projects

```bash
$claude-to-codex git-commit --global
```

Writes to `~/.codex/skills/git-commit/` so the skill is available in every
project on your machine, not just the current one.

---

### Fuzzy name search

```bash
$claude-to-codex "write commit message" --dry-run
```

The skill searches the marketplace with your phrase and shows a numbered list
if multiple results match. You pick one before anything is converted.

```
Found 3 results for "write commit message":

  1. git-commit      (anthropics/skills)   Generate conventional commit messages
  2. commit-helper   (community)           AI-powered commit message writer
  3. conventional-commits (community)      Enforce conventional commit format

Pick a number (1–3):
```

---

### Convert with validation

```bash
$claude-to-codex docx --test
```

After writing the files, runs a full skill-creator validation pass:

```
Skill validation report
  Path:   .codex/skills/docx/SKILL.md
  Mode:   inline

  Frontmatter        [PASS]  name: docx, description: 34 words, no extra fields
  Description        [PASS]  trigger scope clear, includes trigger phrases
  Body               [WARN]  2 lines flagged with # REVIEW
  agents/openai.yaml [PASS]  invocation_policy and display_name present

  Result: PASS WITH WARNINGS

  Review these lines before using the skill:
    Line 47: # REVIEW: Original used "MemoryWrite tool" — no Codex equivalent found.
    Line 83: # REVIEW: Original referenced CLAUDE.md project config — verify AGENTS.md applies.
```

---

### Full pipeline — convert, validate with independent tester

```bash
$claude-to-codex docx --multi-agent --test
```

The strictest mode. Three sub-agents run in sequence:

```
Explorer (gpt-5.4-mini)  →  fetch + analyse
Worker   (gpt-5.4)       →  transform + generate yaml
Tester   (gpt-5.4-mini)  →  cold read validation (no context of how it was built)
```

The tester reads the output files fresh — it has no memory of the transformation
steps. This catches issues the writer misses because it's checking its own work.

---

### Bulk conversion in one session

```bash
$claude-to-codex docx --multi-agent --test --global
$claude-to-codex pptx --multi-agent --test --global
$claude-to-codex xlsx --multi-agent --test --global
```

Use `--multi-agent` for multiple conversions in the same session. Each
conversion gets its own explorer + worker pair, keeping context clean between
runs. `--global` installs all three so they're available in every project.

---

## What changes during transformation

### Tool substitutions

| Claude instruction | Codex equivalent |
|---|---|
| `Use TodoWrite to track progress` | `Track progress in a checklist in your response` |
| `Use TodoRead to check tasks` | `Review your checklist` |
| `Use the Bash tool to run <cmd>` | `Run <cmd> in the shell` |
| `Use the WebSearch tool to find X` | `Search the web for X` |
| `Use the Read tool to open <file>` | `Read the contents of <file>` |
| `Use the Write tool to save to <file>` | `Write the output to <file>` |
| `Use the Task tool to delegate X` | `Spawn one agent with task: "X"` |
| `CLAUDE.md` | `AGENTS.md` |
| `claude.ai artifact` | `standalone HTML artifact` |

### Frontmatter — before and after

```yaml
# Before (Claude) — has extra fields that break Codex validation
---
name: git-commit
description: Generate a conventional Git commit message.
license: MIT
version: 1.2.0
---

# After (Codex) — only name + description, per skill-creator spec
---
name: git-commit
description: >
  Generates a conventional Git commit message from staged changes.
  Use when asked to write a commit, commit staged changes, or generate
  a commit message. Not for branch management or rebasing.
  Invoke with $git-commit.
---
```

### Generated agents/openai.yaml

```yaml
display_name: Git Commit Generator
icon: git-branch          # inferred from skill keywords
brand_color: "#f05032"    # inferred from icon
invocation_policy: explicit
description: Generates a conventional Git commit message from staged changes.
```

---

## Output structure

After running `$claude-to-codex git-commit`:

```
.codex/skills/
  git-commit/
    SKILL.md           ← transformed, Codex-ready skill
    agents/
      openai.yaml      ← generated app metadata
```

---

## Execution modes

```
$claude-to-codex docx
  → You run all 8 steps. Fast, simple.

$claude-to-codex docx --multi-agent
  → Explorer: fetch + analyse
  → Worker:   transform + generate yaml
  → You:      search, confirm, write, report

$claude-to-codex docx --test
  → Same as default + inline validation after writing

$claude-to-codex docx --multi-agent --test
  → Explorer + Worker + independent Tester sub-agent
  → Strictest mode — tester reads output cold
```

---

## Tested on

| Skill | Source | Changes | REVIEW flags | Result |
|---|---|---|---|---|
| `web-artifacts-builder` | anthropics/skills | 4 | 0 | PASS |
| `docx` | anthropics/skills | TBD | TBD | try it → open a PR |
| `pptx` | anthropics/skills | TBD | TBD | try it → open a PR |

---

## Edge cases

| Situation | Behaviour |
|---|---|
| Skill not found | Reports clearly, offers alternate query |
| Fetch fails (all 3 sources) | Lists every URL tried, stops |
| Skill already exists | Asks before overwriting — bypass with `--overwrite` |
| Unknown tool reference | Flags with `# REVIEW`, never silently drops |
| MCP tool reference | Preserves name, adds to `mcp_servers` in openai.yaml |
| Cached web search mode | Warns user, recommends `--search` flag |
| Validation FAIL | Lists every failure, asks fix/proceed before continuing |

---

## Repo structure

```
claude-to-codex/
  SKILL.md                        ← the skill Codex executes
  README.md                       ← you are here
  agents/
    openai.yaml                   ← Codex app metadata for this skill
  references/
    tool-map.md                   ← Claude → Codex substitution rules
    codex-tool-dictionary.md      ← full Codex built-in tool reference
```

---

## Contributing

Found a skill that didn't convert cleanly? Open an issue with:

1. The Claude skill name and source URL
2. The line(s) that caused problems
3. What the correct Codex equivalent should be

PRs especially welcome for additions to `references/tool-map.md` — every
new tool substitution makes the transformer smarter for everyone.

---

## License

MIT — free to use, fork, and build on.
