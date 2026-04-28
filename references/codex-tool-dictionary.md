# Codex tool dictionary

Complete reference of every built-in tool available to a Codex agent.
Used by the `$claude-to-codex` skill during the ANALYSE and TRANSFORM steps
to map Claude-specific tool references to their Codex equivalents.

---

## Tool categories

1. [Shell & file execution](#1-shell--file-execution)
2. [Web search](#2-web-search)
3. [Sub-agent / multi-agent](#3-sub-agent--multi-agent)
4. [JavaScript REPL](#4-javascript-repl)
5. [MCP (external tools)](#5-mcp-external-tools)
6. [Image input](#6-image-input)
7. [Cloud tasks](#7-cloud-tasks)

---

## 1. Shell & file execution

The primary tool in Codex. All file reads, writes, edits, and shell commands
go through shell execution. There is no separate named tool for each operation
— the agent runs shell commands directly.

| Operation | Codex instruction | Notes |
|---|---|---|
| Run a command | `Run <cmd> in the shell` | Codex executes via the configured sandbox |
| Read a file | `Read the contents of <file>` | Agent runs `cat <file>` or equivalent |
| Write a file | `Write the output to <file>` | Agent runs shell write or heredoc |
| Edit a file | `Edit <file> to change <what>` | Agent uses shell tools (sed, awk) or direct edit |
| List directory | `List the files in <dir>` | Agent runs `ls` or `find` |

### Sandbox approval modes

Codex gates shell execution by sandbox policy. Skills should be aware of the
current mode — some operations require explicit user approval.

| Mode | Behaviour | When to use |
|---|---|---|
| `read-only` | Reads only, no writes or commands | Safe exploration |
| `workspace-write` | Full read/write within workspace, no network | Default for coding |
| `danger-full-access` | Full access + network (equivalent to `--yolo`) | Power users only |

### Claude → Codex substitution

| Claude | Codex |
|---|---|
| `Use the Bash tool to run <cmd>` | `Run <cmd> in the shell` |
| `Use the Read tool to open <file>` | `Read the contents of <file>` |
| `Use the Write tool to create <file>` | `Write the output to <file>` |
| `Use the Edit tool to change line N` | `Edit line N in <file>` |
| `Use MultiEdit to apply changes` | `Apply all changes to the file` |
| `Use NotebookEdit to update cell N` | `Edit cell N in the notebook JSON` |

---

## 2. Web search

Built-in, no configuration required for most cases.

### Modes

| Mode | How to enable | Behaviour |
|---|---|---|
| `cached` | Default for local CLI tasks | Pre-indexed OpenAI web cache, faster, lower injection risk |
| `live` | `--search` flag or `web_search = "live"` in config | Real-time fetches, most recent data |
| `disabled` | `web_search = "disabled"` in config | Turns off web search entirely |

> Use `--search` flag when a skill needs current marketplace or registry data
> (e.g. `$claude-to-codex` itself needs live results to find fresh skills).

### Claude → Codex substitution

| Claude | Codex |
|---|---|
| `Use the WebSearch tool to find...` | `Search the web for...` |
| `Call WebSearch with query: X` | `Search for X` |
| `Use WebSearch to look up the latest...` | `Search for the latest X` (add `--search` for live) |

---

## 3. Sub-agent / multi-agent

Codex handles orchestration across agents, including spawning new subagents,
routing follow-up instructions, waiting for results, and closing agent threads.

> Codex only spawns subagents when you explicitly ask it to. Because each
> subagent does its own model and tool work, subagent workflows consume more
> tokens than comparable single-agent runs.

### The five sub-agent tools

| Tool | Purpose | Key parameters |
|---|---|---|
| `spawn_agent` | Create a new child agent thread | `task`, `agent_type`, `nickname_candidates` |
| `send_input` | Send a follow-up message to a running child | `agent_id`, `message` |
| `wait_agent` | Block until one or more children finish | `ids` (list), `timeout_ms` |
| `resume_agent` | Re-activate a paused child thread | `agent_id` |
| `close_agent` | Terminate a child thread | `agent_id` |

> Note: The wait tool was renamed `wait_agent` in a recent release to align
> with `spawn_agent` and `send_input`. Always use `wait_agent` in new skills.

### Batch fan-out tool

| Tool | Purpose |
|---|---|
| `spawn_agents_on_csv` | Read a CSV, spawn one worker per row, collect results back to CSV |

Each worker must call `report_agent_job_result` exactly once. If a worker
exits without reporting, Codex marks that row as an error in the output CSV.

### How to invoke a sub-agent in a SKILL.md

Per Codex docs, the correct prompt pattern is explicit and bounded:

```markdown
## Sub-agent step

Spawn one agent for this task:
- Agent type: explorer
- Task: "Find all API route handlers and return a list of file paths"
- Do not spawn any additional agents.

Wait for the agent to complete using wait_agent, then use its output to proceed.
```

### Config.toml settings

```toml
[features]
multi_agent = true

[agents]
max_threads = 4      # max parallel child agents
max_depth   = 2      # max nesting depth (parent → child → grandchild)
```

### Recommended models per role

| Role | Recommended model | Reason |
|---|---|---|
| Orchestrator / planner | `gpt-5.4` | Complex reasoning, coordination |
| Explorer / reader | `gpt-5.4-mini` | Fast file scan, 3x cheaper |
| Worker / implementer | `gpt-5.4` | Needs strong coding capability |
| Reviewer | `gpt-5.4` | Correctness + security judgment |
| Batch CSV worker | `gpt-5.4-mini` | High volume, lighter reasoning |

### Claude → Codex substitution (sub-agents)

Claude Code uses `Task` tool calls to spawn sub-agents. Codex uses
prompt-mediated spawning via the five tools above.

| Claude | Codex |
|---|---|
| `Use the Task tool to delegate X` | `Spawn one agent with task: "X"` |
| `Spawn a subagent to handle Y` | `Spawn one agent for Y. Do not spawn any additional agents.` |
| `Wait for all agents to complete` | `Wait for all children using wait_agent` |
| `Send follow-up to agent Z` | `Use send_input to send "..." to agent Z` |

---

## 4. JavaScript REPL

An experimental built-in tool for running JavaScript in a sandboxed Node environment.

| Tool | Purpose |
|---|---|
| `js_repl` | Execute JavaScript snippets; access `codex.cwd`, `codex.homeDir`, `codex.tool(...)` |

Enable via:
```toml
[features]
js_repl = true     # requires Node 22.22.0+
```

> Useful for data transformation, JSON manipulation, or quick calculations
> without shelling out. Not suitable for UI or browser code.

---

## 5. MCP (external tools)

Connect Codex to more tools by configuring Model Context Protocol servers.
Add STDIO or streaming HTTP servers in `~/.codex/config.toml` — Codex
launches them automatically when a session starts and exposes their tools
next to the built-ins.

### Config format

```toml
[mcp_servers.my-tool]
command = "npx"
args    = ["-y", "@my-org/my-mcp-server"]
```

### When to use MCP vs built-ins

| Need | Use |
|---|---|
| GitHub PRs, issues | `mcp_servers.github` |
| Databases (Postgres, SQLite) | `mcp_servers.db` |
| Custom internal APIs | `mcp_servers.my-api` |
| File ops, shell, web search | Built-in (no MCP needed) |

### Claude → Codex (MCP tools)

Claude skills that reference specific MCP tools by name should preserve those
references, but they are not auto-trusted. Candidate MCP entries should be
reviewed with the user before anything is written to `agents/openai.yaml`:

```yaml
mcp_servers:
  - name: github
    url: https://mcp.github.com/mcp
```

Only explicitly approved entries with known URLs should be written. Unknown or
declined entries should stay out of YAML and remain visible for manual review in
the transformed skill body.

---

## 6. Image input

Attach screenshots or design specs so Codex can read image details alongside
your prompt. Codex accepts PNG and JPEG via the interactive composer or the
`--image` CLI flag.

In a skill, reference images like:
```markdown
Ask the user to attach a screenshot or design spec if needed.
Codex can read PNG and JPEG images passed via the composer or --image flag.
```

### Claude → Codex substitution

| Claude | Codex |
|---|---|
| `Use the computer_use tool to view the screen` | Not available — ask user to paste a screenshot |
| Accepts images in message content | Same — paste or `--image <path>` on CLI |

---

## 7. Cloud tasks

Run long-horizon tasks in an isolated cloud environment via Codex Cloud.

```bash
codex cloud-tasks submit "Refactor the auth module"
codex cloud-tasks list
```

Not typically invoked from within a skill — this is a user-level workflow.

---

## Master Claude → Codex tool map

| Claude tool | Codex equivalent | Notes |
|---|---|---|
| `Bash` | Shell (natural language) | Core — always available |
| `Read` | Shell `cat` / read file | Via shell |
| `Write` | Shell write / heredoc | Via shell |
| `Edit` / `MultiEdit` | Shell edit | Via shell |
| `WebSearch` | `Search the web for...` | Built-in, cached or live |
| `TodoWrite` / `TodoRead` | Checklist in response | No native equivalent |
| `Task` (sub-agent) | `spawn_agent` (prompt-mediated) | Explicit ask required |
| `NotebookRead/Edit` | Shell JSON edit of `.ipynb` | Via shell |
| `computer_use` | Not available | Ask user for screenshot |
| `/browse` (gstack binary) | `# REVIEW` — no Codex equivalent yet | Flag for manual replacement |
| MCP tools (named) | Same MCP tool name | Declare in `agents/openai.yaml` |

---

## Ready-to-paste sub-agent patterns for SKILL.md

### Spawn one agent (recommended starting point)
```
Spawn exactly one agent for this task.
Use the explorer agent.
Task: "<specific goal>"
Do not spawn any additional agents.
Wait for it to complete using wait_agent, then use its output.
```

### Spawn two agents in parallel
```
Spawn two agents in parallel:
1. Agent type: explorer — Task: "Find all X in the codebase"
2. Agent type: worker  — Task: "Implement Y based on the spec"
Wait for both to complete using wait_agent before proceeding.
```

### Batch CSV fan-out
```
Use spawn_agents_on_csv with:
- csv_path: /tmp/tasks.csv
- id_column: task_id
- instruction: "Process {task_id}: {description}. Call report_agent_job_result with your result."
- output_csv_path: /tmp/results.csv
```
