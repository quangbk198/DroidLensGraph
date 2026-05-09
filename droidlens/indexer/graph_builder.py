"""
Graph builder — orchestrates scanning, parsing, and storing the knowledge graph.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Callable, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from droidlens.indexer.scanner import scan_sources, count_sources
from droidlens.indexer.java_parser import parse_java_file
from droidlens.indexer.kotlin_parser import parse_kotlin_file
from droidlens.graph.storage import GraphStorage, get_db_path

console = Console()

def _update_gitignore(project_path: str):
    gitignore_path = Path(project_path) / ".gitignore"
    entry = ".droidlens/"
    if gitignore_path.exists():
        try:
            content = gitignore_path.read_text(encoding="utf-8")
            if entry not in content.splitlines():
                with gitignore_path.open("a", encoding="utf-8") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(f"{entry}\n")
        except Exception as exc:
            console.print(f"[yellow]⚠ Could not update .gitignore: {exc}[/yellow]")
    else:
        try:
            gitignore_path.write_text(f"{entry}\n", encoding="utf-8")
        except Exception as exc:
            console.print(f"[yellow]⚠ Could not create .gitignore: {exc}[/yellow]")


def build_graph(
    project_path: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> GraphStorage:
    """
    Index an Android project and return an open GraphStorage.
    Caller is responsible for closing the storage.
    """
    db_path = get_db_path(project_path)
    storage = GraphStorage(db_path)
    storage.connect()
    storage.clear()

    files = list(scan_sources(project_path))
    total = len(files)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Indexing {total} files…", total=total)

        for i, (file_path, lang) in enumerate(files):
            progress.update(task, description=f"[cyan]{file_path.name}", advance=1)
            if on_progress:
                on_progress(i + 1, total, str(file_path))

            try:
                if lang == "java":
                    nodes, edges = parse_java_file(str(file_path))
                else:
                    nodes, edges = parse_kotlin_file(str(file_path))

                for node in nodes:
                    storage.upsert_node(node)
                for edge in edges:
                    storage.upsert_edge(edge)

            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]⚠ Skipped {file_path.name}: {exc}")

        storage.commit()

    stats = storage.get_stats()
    storage.set_project_info("path", project_path)
    storage.set_project_info("name", Path(project_path).name)
    storage.set_project_info("indexed_at", datetime.now(timezone.utc).isoformat())
    storage.set_project_info("stats", stats)

    # Automatically add .droidlens/ to .gitignore
    _update_gitignore(project_path)

    return storage
