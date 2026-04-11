# Claude → Codex tool substitution map

This reference is used by the skill during the ANALYSE and TRANSFORM steps.
Any instruction containing a Claude-specific tool name on the left gets
rewritten using the Codex-safe phrasing on the right.

---

## Tool substitutions

### TodoWrite / TodoRead

These are Claude Code's built-in task-tracking tools. Codex has no equivalent.

| Claude | Codex |
|---|---|
| `Use TodoWrite to create a task list` | `Track your progress using a numbered checklist in your response` |
| `Use TodoWrite to mark X as complete` | `Update your checklist to mark X as done` |
| `Use TodoRead to check remaining tasks` | `Review the checklist you created at the start` |
| `Update the todo list with status` | `Note the current status in your response` |

### Bash (shell execution)

Both agents support shell execution, but the tool name differs.

| Claude | Codex |
|---|---|
| `Use the Bash tool to run <cmd>` | `Run <cmd> in the shell` |
| `Call Bash with command: <cmd>` | `Execute: <cmd>` |
| `Run this in a Bash tool call` | `Run this in a shell command` |

Note: `Bash` as a generic term ("run a bash script") is fine and needs no change.
Only the specific `Bash tool` / `Bash tool call` phrasing is Claude-specific.

### WebSearch (Claude's built-in)

Claude Code has a built-in `WebSearch` tool. Codex uses its own web search.
Rewrite to be model-agnostic — both agents will use their own search capability.

| Claude | Codex |
|---|---|
| `Use the WebSearch tool to find...` | `Search the web for...` |
| `Call WebSearch with query: X` | `Search for X` |
| `Use WebSearch to look up...` | `Look up...` |

### Read / Write / Edit (file tools)

Claude Code has named tools for file operations. Codex uses shell commands.

| Claude | Codex |
|---|---|
| `Use the Read tool to open file X` | `Read the contents of file X` |
| `Use the Write tool to save to X` | `Write the output to X` |
| `Use the Edit tool to change line N` | `Edit line N in file X` |
| `Use MultiEdit to apply changes` | `Apply all changes to the file` |

### NotebookRead / NotebookEdit

Jupyter-specific Claude tools. Codex has no direct equivalent.

| Claude | Codex |
|---|---|
| `Use NotebookRead to inspect the notebook` | `Read the .ipynb file as JSON` |
| `Use NotebookEdit to update cell N` | `Edit cell N in the notebook JSON` |

---

## Frontmatter fields

### Remove from Codex output

These Claude-specific frontmatter fields have no meaning in Codex:

- `license` — remove (or move to README.md)
- `model` — remove (Codex uses its own model)
- `version` — remove unless explicitly needed
- `author_url` — remove

### Preserve as-is

- `name`
- `description` — preserve and rewrite so it clearly explains when the skill
  should trigger, when it should not trigger, and how to invoke it
- no frontmatter fields other than `name` and `description` are valid in the
  converted output

---

## Phrases to flag with # REVIEW

When the skill uses language the transformer cannot confidently rewrite,
flag the line for manual review rather than silently changing it:

- Any reference to a tool name not in this map
- `"use the X tool"` where X is unknown
- References to Claude.ai-specific UI features
- References to `CLAUDE.md` or Claude-specific config files

Example output:
```markdown
# REVIEW: Original said "use the MemoryWrite tool" — no Codex equivalent found.
# Replace with your preferred note-taking approach or remove this step.
```

---

## What NOT to change

- All reasoning and decision-making instructions
- Formatting rules (output structure, markdown, headers)
- Workflow logic (steps, conditions, branching)
- Domain-specific instructions (git commands, file formats, APIs)
- References to standard shell tools (grep, sed, awk, curl, etc.)
- MCP tool names in the body (preserve them, but require explicit approval
  before adding any `mcp_servers` entries to `agents/openai.yaml`)
