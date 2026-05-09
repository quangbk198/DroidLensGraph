# DroidLens

> **Knowledge graph indexer for Android codebases (Java/Kotlin)**
> Indexes every class, method, field, dependency and call chain — then exposes it via MCP tools so AI agents never miss code.

---

## Quick Start

### 1. Install
```bash
cd D:\DroidLens
pip install -e .
```

### 2. Index your Android project
```bash
droidlens index "D:\path\to\your\AndroidProject"
```

### 3. Open the graph browser
```bash
droidlens serve --project "D:\path\to\your\AndroidProject" --port 7070
# Opens http://127.0.0.1:7070 automatically
```

### 4. Use with AI agents (MCP)
```bash
droidlens mcp --project "D:\path\to\your\AndroidProject"
```

---

## CLI Commands

| Command | Description |
|---|---|
| `droidlens index <path>` | Index an Android project |
| `droidlens serve --project <path>` | Launch graph browser UI |
| `droidlens mcp --project <path>` | Start MCP stdio server |
| `droidlens stats --project <path>` | Print graph statistics |

---

## MCP Configuration (Claude Desktop / Cursor)

Add to your MCP config file (`claude_desktop_config.json` or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "droidlens": {
      "command": "droidlens",
      "args": ["mcp", "--project", "D:\\path\\to\\your\\AndroidProject"]
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|---|---|
| `get_stats` | Node/edge counts by type |
| `search_nodes` | Search classes, methods by name |
| `get_class_info` | Full class info: members, superclass, interfaces |
| `find_usages` | All callers/references of a method or class |
| `get_call_chain` | BFS call chain from a method (depth configurable) |
| `get_dependencies` | All dependencies of a class |
| `list_classes` | List all classes with optional package/type filter |
| `index_project` | Re-index a project on demand |

---

## Graph Browser Features

- **Dark mode** UI with colour-coded node types
- **Multiple layouts**: Dagre (hierarchical), CoSE, Circle, Grid, Concentric
- **Filters**: Toggle node types on/off
- **Search**: Live search → click to focus + highlight neighbourhood
- **Detail panel**: Click any node for full info + related edges
- **Zoom controls**: +/− and fit-to-screen

---

## Node Types & Colours

| Type | Colour | Description |
|---|---|---|
| Class | Purple | Kotlin/Java class |
| AbstractClass | Light purple | Abstract class |
| Interface | Teal | Interface |
| Enum | Orange | Enum class |
| Object | Sky blue | Kotlin object / companion |
| Method | Pink | Method or function |
| Property | Green | Kotlin property |
| Field | Light green | Java field |

## Edge Types

| Edge | Meaning |
|---|---|
| CONTAINS | Class contains method/field |
| EXTENDS | Inheritance |
| IMPLEMENTS | Interface implementation |
| CALLS | Method call |
| OVERRIDES | Method override |
| USES | Type usage |

---

## Where is the index stored?

The graph database is stored at:
```
<your-project>/.droidlens/graph.db
```
It's a standard SQLite file — you can query it directly with any SQLite tool.
