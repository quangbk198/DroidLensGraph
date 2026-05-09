"""
SQLite-backed storage for the DroidLens knowledge graph.
All data is stored in .droidlens/graph.db inside the indexed project.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from droidlens.graph.models import Node, Edge, NodeType, EdgeType, ProjectInfo


class GraphStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id            TEXT PRIMARY KEY,
                type          TEXT NOT NULL,
                name          TEXT NOT NULL,
                qualified_name TEXT,
                file_path     TEXT,
                line_number   INTEGER DEFAULT 0,
                package_name  TEXT,
                language      TEXT,
                is_abstract   INTEGER DEFAULT 0,
                visibility    TEXT DEFAULT 'public',
                annotations   TEXT DEFAULT '[]',
                metadata      TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS edges (
                id        TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type      TEXT NOT NULL,
                metadata  TEXT DEFAULT '{}',
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );

            CREATE TABLE IF NOT EXISTS project_info (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
            CREATE INDEX IF NOT EXISTS idx_nodes_package ON nodes(package_name);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def upsert_node(self, node: Node):
        self._conn.execute("""
            INSERT INTO nodes
                (id, type, name, qualified_name, file_path, line_number,
                 package_name, language, is_abstract, visibility, annotations, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                type=excluded.type, name=excluded.name,
                qualified_name=excluded.qualified_name,
                file_path=excluded.file_path, line_number=excluded.line_number,
                package_name=excluded.package_name, language=excluded.language,
                is_abstract=excluded.is_abstract, visibility=excluded.visibility,
                annotations=excluded.annotations, metadata=excluded.metadata
        """, (
            node.id, node.type.value, node.name, node.qualified_name,
            node.file_path, node.line_number, node.package_name, node.language,
            int(node.is_abstract), node.visibility,
            json.dumps(node.annotations), json.dumps(node.metadata),
        ))

    def upsert_edge(self, edge: Edge):
        self._conn.execute("""
            INSERT INTO edges (id, source_id, target_id, type, metadata)
            VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                source_id=excluded.source_id, target_id=excluded.target_id,
                type=excluded.type, metadata=excluded.metadata
        """, (
            edge.id, edge.source_id, edge.target_id, edge.type.value,
            json.dumps(edge.metadata),
        ))

    def commit(self):
        self._conn.commit()

    def clear(self):
        self._conn.executescript("DELETE FROM nodes; DELETE FROM edges; DELETE FROM project_info;")
        self._conn.commit()

    def set_project_info(self, key: str, value: Any):
        self._conn.execute(
            "INSERT INTO project_info(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value))
        )
        self._conn.commit()

    def get_project_info(self, key: str) -> Any:
        row = self._conn.execute("SELECT value FROM project_info WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else None

    # ------------------------------------------------------------------
    # Read — nodes
    # ------------------------------------------------------------------
    def _row_to_node(self, row) -> Node:
        return Node(
            id=row["id"], type=NodeType(row["type"]), name=row["name"],
            qualified_name=row["qualified_name"] or "",
            file_path=row["file_path"] or "",
            line_number=row["line_number"] or 0,
            package_name=row["package_name"] or "",
            language=row["language"] or "",
            is_abstract=bool(row["is_abstract"]),
            visibility=row["visibility"] or "public",
            annotations=json.loads(row["annotations"] or "[]"),
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def get_all_nodes(self) -> List[Node]:
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return [self._row_to_node(r) for r in rows]

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        rows = self._conn.execute("SELECT * FROM nodes WHERE type=?", (node_type.value,)).fetchall()
        return [self._row_to_node(r) for r in rows]

    def get_node(self, node_id: str) -> Optional[Node]:
        row = self._conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def search_nodes(self, query: str) -> List[Node]:
        q = f"%{query}%"
        rows = self._conn.execute(
            "SELECT * FROM nodes WHERE name LIKE ? OR qualified_name LIKE ? LIMIT 50",
            (q, q)
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    # ------------------------------------------------------------------
    # Read — edges
    # ------------------------------------------------------------------
    def _row_to_edge(self, row) -> Edge:
        return Edge(
            id=row["id"], source_id=row["source_id"], target_id=row["target_id"],
            type=EdgeType(row["type"]), metadata=json.loads(row["metadata"] or "{}"),
        )

    def get_all_edges(self) -> List[Edge]:
        rows = self._conn.execute("SELECT * FROM edges").fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_edges_from(self, node_id: str) -> List[Edge]:
        rows = self._conn.execute("SELECT * FROM edges WHERE source_id=?", (node_id,)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_edges_to(self, node_id: str) -> List[Edge]:
        rows = self._conn.execute("SELECT * FROM edges WHERE target_id=?", (node_id,)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[Edge]:
        rows = self._conn.execute("SELECT * FROM edges WHERE type=?", (edge_type.value,)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        node_count = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        type_rows = self._conn.execute(
            "SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type"
        ).fetchall()
        edge_rows = self._conn.execute(
            "SELECT type, COUNT(*) as cnt FROM edges GROUP BY type"
        ).fetchall()
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "nodes_by_type": {r["type"]: r["cnt"] for r in type_rows},
            "edges_by_type": {r["type"]: r["cnt"] for r in edge_rows},
        }


def get_db_path(project_path: str) -> str:
    return str(Path(project_path) / ".droidlens" / "graph.db")
