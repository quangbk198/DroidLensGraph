# -*- coding: utf-8 -*-
"""
DroidLens Scaffold

After a successful `droidlens index`, this module:
  1. Creates .agents/skills/droidlens/ with all skill SKILL.md files.
  2. Creates or updates AGENTS.md with a <!-- droidlens:start/end --> block.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Skill content templates
# ---------------------------------------------------------------------------

SKILLS: dict[str, dict[str, str]] = {
    "droidlens-cli": {
        "name": "droidlens-cli",
        "description": (
            'Use when the user needs to run DroidLens CLI commands like index a project, '
            'serve the graph browser, start the MCP server, or check stats. '
            'Examples: "Index this Android project", "Start the graph browser", "Show graph stats"'
        ),
        "content": """\
# DroidLens CLI Commands

All commands work via the `droidlens` entry-point (installed with `pip install -e .`).

## Commands

### index — Build or refresh the knowledge graph

```bash
droidlens index <path>
droidlens index .          # index current directory
```

Parses all Java/Kotlin source files under `<path>`, builds the knowledge graph, writes it to
`.droidlens/graph.db`, and scaffolds `.agents/skills/droidlens/` + updates `AGENTS.md`.

| Flag     | Effect                                   |
| -------- | ---------------------------------------- |
| *(none)* | Default `.` if no path provided          |

**When to run:** First time in a project, after major refactors, or when the MCP server
reports the index is stale.

---

### serve — Launch the graph browser UI

```bash
droidlens serve --project <path>
droidlens serve --project . --port 8080
```

Opens a browser-based interactive graph at `http://127.0.0.1:7070` (default port).

| Option      | Default       | Description                        |
| ----------- | ------------- | ---------------------------------- |
| `--project` | `.`           | Path to indexed Android project    |
| `--port`    | `7070`        | HTTP port for the graph browser    |
| `--host`    | `127.0.0.1`   | Host to bind to                    |

---

### mcp — Start the MCP stdio server

```bash
droidlens mcp --project <path>
```

Starts a Model Context Protocol stdio server so AI agents (Claude, etc.) can call
DroidLens tools directly.  The `--project` flag is optional; tools can index on demand.

---

### stats — Print graph statistics

```bash
droidlens stats --project <path>
```

Shows node/edge counts, breakdown by type, and when the project was last indexed.

---

### clean — Delete graph indexes

```bash
droidlens clean <path>
droidlens clean --all --force
```

Deletes the index for the specified project, or all projects if `--all` is used. Use this to clear stale databases or reset the global registry.

---

## After Indexing

1. Run `droidlens serve --project <path>` to explore the graph visually
2. Or start `droidlens mcp --project <path>` for AI agent integration
3. Use the other DroidLens skills (`exploring`, `debugging`, `impact-analysis`, `refactoring`)

## Troubleshooting

- **"No index found"**: Run `droidlens index <path>` first
- **Port already in use**: Pass `--port <other>` to `serve`
- **Graph appears stale**: Re-run `droidlens index <path>` then restart `droidlens mcp`
""",
    },

    "droidlens-exploring": {
        "name": "droidlens-exploring",
        "description": (
            'Use when the user asks how Android code works, wants to understand class '
            'hierarchies, call chains, or module structure. '
            'Examples: "How does X work?", "What calls this method?", "Show me the auth flow"'
        ),
        "content": """\
# Exploring Android Codebases with DroidLens

## When to Use

- "How does authentication work?"
- "What's the project structure?"
- "Show me the main components / classes"
- "Where is the network layer?"
- Understanding code you haven't seen before

## Workflow

```
1. droidlens_get_stats()                         → Verify index exists and is fresh
2. droidlens_search_nodes({query: "<concept>"})  → Find relevant classes / methods
3. droidlens_get_node({id: <nodeId>})            → Inspect a specific node
4. droidlens_get_neighbors({id: <nodeId>})       → Explore callers / callees / dependencies
5. droidlens_get_call_chain({...})               → Trace a full call chain
```

> If `get_stats` shows 0 nodes → run `droidlens index <path>` in terminal first.

## Checklist

```
- [ ] droidlens_get_stats() to confirm index is loaded
- [ ] droidlens_search_nodes for the concept you want to understand
- [ ] Review returned classes / methods with file locations
- [ ] droidlens_get_neighbors on key nodes for callers / dependencies
- [ ] droidlens_get_call_chain for full execution traces
- [ ] Read source files for implementation details
```

## Tools

**droidlens_search_nodes** — full-text search across all graph nodes:

```
droidlens_search_nodes({query: "payment", limit: 10})
→ PaymentActivity  (app/src/main/java/.../PaymentActivity.kt:1)
→ PaymentViewModel (app/src/main/.../PaymentViewModel.kt:1)
→ processPayment   (PaymentRepository.kt:42)
```

**droidlens_get_neighbors** — callers, callees, and relationships:

```
droidlens_get_neighbors({id: 123, direction: "both"})
→ Incoming: CheckoutActivity.onPay() → processPayment
→ Outgoing: processPayment → validateCard, chargeGateway
```

**droidlens_get_call_chain** — trace a complete call chain:

```
droidlens_get_call_chain({from_id: 10, to_id: 55})
→ CheckoutActivity.onPay
  → PaymentViewModel.submit
    → PaymentRepository.processPayment
      → GatewayApi.charge
```

## Example: "How does the login flow work?"

```
1. droidlens_search_nodes({query: "login"})
   → LoginActivity, LoginViewModel, AuthRepository

2. droidlens_get_neighbors({id: <LoginActivity.id>})
   → Outgoing: LoginViewModel.login(), LoginViewModel.validateInput()

3. droidlens_get_call_chain({from_id: <LoginActivity>, to_id: <AuthRepository>})
   → LoginActivity → LoginViewModel.login → AuthRepository.authenticate → AuthApi.login
```
""",
    },

    "droidlens-impact-analysis": {
        "name": "droidlens-impact-analysis",
        "description": (
            'Use when the user wants to know what will break if they change something in the Android codebase, '
            'or needs safety analysis before editing. '
            'Examples: "Is it safe to change X?", "What depends on this class?", "What will break?"'
        ),
        "content": """\
# Impact Analysis with DroidLens

## When to Use

- "Is it safe to change this method?"
- "What will break if I modify X?"
- "Show me the blast radius"
- "Who uses this class?"
- Before making non-trivial code changes

## Workflow

```
1. droidlens_search_nodes({query: "X"})               → Find the target node(s)
2. droidlens_get_neighbors({id, direction: "incoming"}) → Direct callers / dependents
3. droidlens_get_call_chain({...})                     → Trace upstream paths
4. Assess risk level and report to user
```

> Re-index first if stats show 0 nodes: `droidlens index <path>`

## Checklist

```
- [ ] droidlens_search_nodes to locate the target symbol
- [ ] droidlens_get_neighbors (incoming) to find direct callers
- [ ] Review high-confidence dependencies first
- [ ] droidlens_get_call_chain for upstream traces
- [ ] Assess risk level and report to user before editing
```

## Risk Assessment

| Callers / Dependents        | Risk     |
| --------------------------- | -------- |
| 0–3 direct callers          | LOW      |
| 4–9 or cross-module callers | MEDIUM   |
| 10+ or critical path        | HIGH     |
| Auth, payment, data-sync    | CRITICAL |

## Understanding `get_neighbors` Output

| Direction  | Meaning                              |
| ---------- | ------------------------------------ |
| `incoming` | What CALLS / USES this node (d=1)    |
| `outgoing` | What this node CALLS / USES          |
| `both`     | Full neighbourhood                   |

## Example: "What breaks if I change AuthRepository.authenticate?"

```
1. droidlens_search_nodes({query: "AuthRepository.authenticate"})
   → node id: 42

2. droidlens_get_neighbors({id: 42, direction: "incoming"})
   → LoginViewModel.login (LoginViewModel.kt:35)
   → SsoViewModel.ssoLogin (SsoViewModel.kt:22)

3. droidlens_get_call_chain({from_id: <LoginActivity>, to_id: 42})
   → LoginActivity → LoginViewModel.login → AuthRepository.authenticate

4. Risk: 2 direct callers, cross-module = MEDIUM
   ⚠ Warn user before proceeding.
```
""",
    },

    "droidlens-debugging": {
        "name": "droidlens-debugging",
        "description": (
            'Use when the user is debugging a bug, tracing an error, or asking why something fails in the Android app. '
            'Examples: "Why is X failing?", "Where does this crash come from?", "Trace this NullPointerException"'
        ),
        "content": """\
# Debugging Android Code with DroidLens

## When to Use

- "Why is this Activity crashing?"
- "Trace where this exception comes from"
- "Who calls this method that throws?"
- "This ViewModel returns wrong data"
- Investigating crashes, ANRs, or unexpected behavior

## Workflow

```
1. droidlens_search_nodes({query: "<class or method near error>"}) → Find related nodes
2. droidlens_get_node({id: <nodeId>})                              → Inspect the suspect
3. droidlens_get_neighbors({id, direction: "incoming"})            → Who calls it?
4. droidlens_get_call_chain({from_id, to_id})                      → Trace full call path
```

> Re-index if `get_stats` shows 0 nodes: `droidlens index <path>`

## Checklist

```
- [ ] Understand the symptom (crash message, wrong behavior)
- [ ] droidlens_search_nodes for the class/method at the crash site
- [ ] droidlens_get_neighbors to see callers
- [ ] droidlens_get_call_chain to trace the full execution path
- [ ] Read source files to confirm root cause
```

## Debugging Patterns

| Symptom                  | DroidLens Approach                                              |
| ------------------------ | --------------------------------------------------------------- |
| NullPointerException     | `search_nodes` for the class → `get_neighbors` incoming callers |
| Wrong ViewModel state    | `get_call_chain` from Activity → ViewModel → Repository         |
| Network error            | `search_nodes` for Repository/Api → trace outgoing calls        |
| Crash in background task | `get_neighbors` on the coroutine dispatcher / worker class      |
| Recent regression        | Re-index and compare `get_stats` before/after                   |

## Example: "LoginActivity crashes on launch"

```
1. droidlens_search_nodes({query: "LoginActivity"})
   → node id: 10

2. droidlens_get_node({id: 10})
   → file: app/src/main/java/.../LoginActivity.kt, line 1

3. droidlens_get_neighbors({id: 10, direction: "outgoing"})
   → Calls: LoginViewModel.init, SessionManager.restore

4. droidlens_get_neighbors({id: <SessionManager>, direction: "outgoing"})
   → Calls: SharedPreferences.getString (may throw if key missing)

5. Root cause: SessionManager.restore reads a key that doesn't exist on first launch
```
""",
    },

    "droidlens-refactoring": {
        "name": "droidlens-refactoring",
        "description": (
            'Use when the user wants to rename, move, extract, or restructure Android code safely. '
            'Examples: "Rename this class", "Extract this into a use-case", "Move this to a new module"'
        ),
        "content": """\
# Refactoring Android Code with DroidLens

## When to Use

- "Rename this class / method safely"
- "Extract this into a UseCase"
- "Move this Repository to a new module"
- "Split this ViewModel"
- Any rename, extract, split, or restructure task

## Workflow

```
1. droidlens_search_nodes({query: "X"})                → Locate target node
2. droidlens_get_neighbors({id, direction: "incoming"}) → Map all callers (d=1)
3. droidlens_get_call_chain({...})                      → Trace upstream paths
4. Plan update order: interfaces → implementations → callers → tests
5. Make changes, then re-run `droidlens index` to verify the new graph
```

> Re-index after refactoring to confirm the new graph is consistent.

## Checklists

### Rename Class or Method

```
- [ ] droidlens_search_nodes to find the target
- [ ] droidlens_get_neighbors (incoming) to find all call sites
- [ ] Perform rename in IDE (use IDE's "Rename" refactor for safety)
- [ ] Re-run droidlens index <path>
- [ ] droidlens_get_stats() to confirm graph rebuilt cleanly
- [ ] droidlens_search_nodes for the new name to verify all references
```

### Extract UseCase / Repository

```
- [ ] droidlens_get_neighbors on the source class — see all callers
- [ ] Identify methods to extract
- [ ] Create new UseCase / Repository class
- [ ] Update callers one by one
- [ ] Re-run droidlens index and verify with droidlens_search_nodes
```

### Move to New Module

```
- [ ] droidlens_search_nodes for all classes in the feature
- [ ] droidlens_get_neighbors to find cross-module dependencies
- [ ] Resolve dependency direction (module A must not import module B if B imports A)
- [ ] Move files, update imports
- [ ] Re-run droidlens index and check get_stats for errors
```

## Risk Rules

| Risk Factor              | Mitigation                                     |
| ------------------------ | ---------------------------------------------- |
| Many callers (>5)        | Use IDE refactor tools + manual review         |
| Cross-module references  | Map with get_neighbors before moving           |
| String references (DI)  | Search source for string literals of the name  |
| Public API / SDK         | Version and deprecate before removal           |

## Example: Rename `AuthRepository` to `AuthDataSource`

```
1. droidlens_search_nodes({query: "AuthRepository"})
   → node id: 77  (AuthRepository.kt:1)

2. droidlens_get_neighbors({id: 77, direction: "incoming"})
   → LoginViewModel.kt:12
   → SsoViewModel.kt:8
   → UserProfileViewModel.kt:31

3. Use Android Studio "Rename" refactor → updates all 3 callers

4. droidlens index .

5. droidlens_search_nodes({query: "AuthDataSource"})
   → Confirms new name is indexed with correct edges
```
""",
    },

    "droidlens-guide": {
        "name": "droidlens-guide",
        "description": (
            'Use when the user asks about DroidLens itself — available MCP tools, how to query the graph, '
            'or general workflow reference. '
            'Examples: "What DroidLens tools are available?", "How do I use DroidLens?"'
        ),
        "content": """\
# DroidLens Guide

Quick reference for all DroidLens MCP tools and the recommended workflow for AI agents.

## Always Start Here

For any task involving Android code understanding, debugging, impact analysis, or refactoring:

1. **`droidlens_get_stats()`** — verify the index exists and is fresh
2. **Match your task to a skill below** and read that skill file
3. **Follow the skill's workflow and checklist**

> If `get_stats` shows 0 nodes → run `droidlens index <path>` in the terminal first.

## Skills

| Task                                              | Skill to read                  |
| ------------------------------------------------- | ------------------------------ |
| Understand architecture / "How does X work?"      | `droidlens-exploring`          |
| Blast radius / "What breaks if I change X?"       | `droidlens-impact-analysis`    |
| Trace bugs / "Why is X failing?"                  | `droidlens-debugging`          |
| Rename / extract / split / move code              | `droidlens-refactoring`        |
| Tools & workflow reference                        | `droidlens-guide` (this file)  |
| Index, serve, mcp, stats CLI commands             | `droidlens-cli`                |

## MCP Tools Reference

| Tool                      | What it gives you                                             |
| ------------------------- | ------------------------------------------------------------- |
| `droidlens_get_stats`     | Node/edge counts, index freshness check                       |
| `droidlens_search_nodes`  | Full-text search across all classes, methods, files           |
| `droidlens_get_node`      | Detailed info for a single node (type, file, line, doc)       |
| `droidlens_get_neighbors` | Callers, callees, and relationships for a node                |
| `droidlens_get_call_chain`| Full call chain trace between two nodes                       |
| `droidlens_list_classes`  | List all indexed classes with optional type filter            |
| `droidlens_impact`        | Blast radius analysis (BFS on incoming edges)                 |
| `droidlens_sql_query`     | Run raw SQLite queries against the graph database             |

## Typical Exploration Flow

```
droidlens_get_stats()
  → 1 234 nodes, 5 678 edges — index is fresh

droidlens_search_nodes({query: "checkout"})
  → CheckoutActivity (id: 10)
  → CheckoutViewModel (id: 11)
  → CheckoutRepository (id: 12)

droidlens_get_neighbors({id: 10, direction: "outgoing"})
  → CheckoutActivity → CheckoutViewModel.startCheckout()
  → CheckoutActivity → AnalyticsTracker.logEvent()

droidlens_get_call_chain({from_id: 10, to_id: 12})
  → CheckoutActivity → CheckoutViewModel.startCheckout
    → CheckoutRepository.placeOrder → PaymentApi.charge
```

## Graph Node Types

| Type        | Description                                |
| ----------- | ------------------------------------------ |
| `CLASS`     | Java / Kotlin class or object              |
| `INTERFACE` | Java / Kotlin interface                    |
| `METHOD`    | Method or function                         |
| `FIELD`     | Class field / property                     |
| `FILE`      | Source file                                |

## Graph Edge Types

| Type       | Description                                 |
| ---------- | ------------------------------------------- |
| `CALLS`    | Method A calls Method B                     |
| `EXTENDS`  | Class A extends Class B                     |
| `IMPLEMENTS` | Class A implements Interface B            |
| `USES`     | Class A holds a reference to Class B        |
| `CONTAINS` | File / Class contains a method or field     |
""",
    },
}

# ---------------------------------------------------------------------------
# AGENTS.md block content generator
# ---------------------------------------------------------------------------

AGENTS_MD_BLOCK_TEMPLATE = """\
<!-- droidlens:start -->
# DroidLens — Android Code Intelligence

This project is indexed by DroidLens. Use the DroidLens MCP tools to explore the Android codebase,
trace call chains, assess impact, and navigate safely.

> If any DroidLens tool reports 0 nodes, run `droidlens index <path>` in terminal first.

## Always Do

- **MUST run impact analysis before editing any class or method.** Before modifying, call
  `droidlens_get_neighbors({{id, direction: "incoming"}})` and check the blast radius (direct callers,
  risk level) before proceeding.
- **MUST warn the user** if the incoming caller count is HIGH (>9) or CRITICAL (auth/payment path)
  before making edits.
- When exploring unfamiliar code, use `droidlens_search_nodes({{query: "concept"}})` to find relevant
  classes/methods instead of grepping. It searches the full knowledge graph.
- When you need full context on a specific node — callers, callees — use
  `droidlens_get_neighbors({{id, direction: "both"}})`.

## Never Do

- NEVER edit a class or method without first checking incoming callers with `droidlens_get_neighbors`.
- NEVER ignore HIGH or CRITICAL caller-count warnings.
- NEVER rename symbols with find-and-replace — use the IDE's safe rename refactor after mapping
  callers with DroidLens.
- NEVER assume the graph is fresh — call `droidlens_get_stats()` at the start of every session.

## MCP Tools

| Tool                      | Use for                                              |
| ------------------------- | ---------------------------------------------------- |
| `droidlens_get_stats`     | Verify index freshness, node/edge counts             |
| `droidlens_search_nodes`  | Find classes/methods by name or concept              |
| `droidlens_get_node`      | Inspect a single node (file, line, type, doc)        |
| `droidlens_get_neighbors` | Callers, callees, and relationships for a node       |
| `droidlens_get_call_chain`| Trace a full call chain between two nodes            |
| `droidlens_list_classes`  | List all indexed classes                             |
| `droidlens_impact`        | Blast radius analysis (BFS on incoming edges)        |
| `droidlens_sql_query`     | Run raw SQLite queries against the graph database    |

## CLI

| Task                                              | Read this skill file                                   |
| ------------------------------------------------- | ------------------------------------------------------ |
| Understand architecture / "How does X work?"      | `.agents/skills/droidlens/droidlens-exploring/SKILL.md`     |
| Blast radius / "What breaks if I change X?"       | `.agents/skills/droidlens/droidlens-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?"                  | `.agents/skills/droidlens/droidlens-debugging/SKILL.md`     |
| Rename / extract / split / move code              | `.agents/skills/droidlens/droidlens-refactoring/SKILL.md`   |
| Tools & workflow reference                        | `.agents/skills/droidlens/droidlens-guide/SKILL.md`         |
| Index, serve, mcp, stats CLI commands             | `.agents/skills/droidlens/droidlens-cli/SKILL.md`           |

<!-- droidlens:end -->
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scaffold_project(project_path: str, project_name: str | None = None) -> None:
    """Create / update .agents/skills/droidlens/ and AGENTS.md in *project_path*."""
    root = Path(project_path).resolve()
    _scaffold_skills(root)
    _scaffold_agents_md(root, project_name or root.name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scaffold_skills(root: Path) -> None:
    """Write SKILL.md files into .agents/skills/droidlens/<skill-name>/."""
    skills_root = root / ".agents" / "skills" / "droidlens"
    skills_root.mkdir(parents=True, exist_ok=True)

    for skill_key, skill in SKILLS.items():
        skill_dir = skills_root / skill_key
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        frontmatter = (
            f"---\n"
            f"name: {skill['name']}\n"
            f'description: "{skill["description"]}"\n'
            f"---\n\n"
        )
        skill_file.write_text(frontmatter + skill["content"], encoding="utf-8")


def _scaffold_agents_md(root: Path, project_name: str) -> None:
    """Create AGENTS.md if absent, or append the droidlens block if not already present."""
    agents_md = root / "AGENTS.md"
    block = AGENTS_MD_BLOCK_TEMPLATE

    if not agents_md.exists():
        agents_md.write_text(block, encoding="utf-8")
        return

    existing = agents_md.read_text(encoding="utf-8")

    # If the block is already injected, update it in-place
    start_tag = "<!-- droidlens:start -->"
    end_tag = "<!-- droidlens:end -->"

    if start_tag in existing and end_tag in existing:
        # Replace the existing block
        before = existing[: existing.index(start_tag)]
        after = existing[existing.index(end_tag) + len(end_tag):]
        updated = before + block.strip() + "\n" + after
        agents_md.write_text(updated, encoding="utf-8")
    else:
        # Append the block at the end
        separator = "\n" if existing.endswith("\n") else "\n\n"
        agents_md.write_text(existing + separator + block, encoding="utf-8")
