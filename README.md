# 🔍 DroidLens

> **Knowledge graph indexer for Android codebases (Java/Kotlin)**  
> Indexes every class, method, field, dependency, and call chain — then exposes it via MCP tools so AI agents never miss code.

---

## 🚀 Installation

### Prerequisites
- **Python 3.10+** installed on your system.

### Steps
1. Navigate to the DroidLens source directory:
   ```bash
   cd D:\DroidLens
   ```
2. Install in editable mode:
   ```bash
   pip install -e .
   ```
   *Note: If `pip install -e .` fails, you can install dependencies manually:*
   ```bash
   pip install -r requirements.txt
   ```

---

## 🛠️ Usage

### 1. Index your Android project
Scan and build the knowledge graph for your project:
```bash
# Using absolute path
python -m droidlens index "C:\path\to\your\AndroidProject"

# OR navigate to your project and run:
python -m droidlens index
```

### 2. Launch the Graph Browser
Explore your codebase visually in the browser (default: `http://127.0.0.1:7070`):
```bash
python -m droidlens serve "C:\path\to\your\AndroidProject"
```

---

## 🤖 AI Agent Integration (MCP)

To use DroidLens with **Cursor**, **Claude Desktop**, or any MCP-compatible agent, add the following to your configuration file:

```json
{
  "mcpServers": {
    "droidlens": {
      "command": "python",
      "args": ["-m", "droidlens", "mcp"] 
    }
  }
}
```

---

## 📊 CLI Commands Reference

| Command | Description |
|---|---|
| `python -m droidlens index <path>` | Index an Android project |
| `python -m droidlens serve <path>` | Launch graph browser UI |
| `python -m droidlens mcp` | Start MCP stdio server |
| `python -m droidlens stats <path>` | Print graph statistics |
| `python -m droidlens list` | List all registered projects |

---

## 🧬 Graph Schema

### Node Types & Colors
| Type | Color | Description |
|---|---|---|
| **Class** | 🟪 Purple | Kotlin/Java class |
| **Interface** | 🟦 Teal | Interface |
| **Method** | 🟥 Pink | Method or function |
| **Field/Property** | 🟩 Green | Java field or Kotlin property |
| **Object** | 🧊 Sky Blue | Kotlin object / companion |

### Edge Types
| Edge | Meaning |
|---|---|
| `CONTAINS` | Class contains method/field |
| `EXTENDS` | Inheritance |
| `IMPLEMENTS` | Interface implementation |
| `CALLS` | Method A calls Method B |
| `USES` | Type usage / reference |

---

## 📂 Storage
The graph database is stored locally in your project:
`YourProject/.droidlens/graph.db` (Standard SQLite file)
