"""
Kotlin source parser using tree-sitter.
Extracts: packages, classes, interfaces, objects, functions, properties,
inheritance (delegation_specifiers), and call expressions.
"""
from pathlib import Path
from typing import List, Tuple, Optional
import hashlib

import tree_sitter_kotlin as tskotlin
from tree_sitter import Language, Parser, Node as TSNode

from droidlens.graph.models import Node, Edge, NodeType, EdgeType

KOTLIN_LANGUAGE = Language(tskotlin.language())
_parser = Parser(KOTLIN_LANGUAGE)


def _node_text(node: TSNode, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()


def _uid(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _get_package(root: TSNode, src: bytes) -> str:
    for child in root.children:
        if child.type == "package_header":
            # Find the qualified_identifier child
            for sub in child.children:
                if sub.type == "qualified_identifier":
                    return _node_text(sub, src).strip()
            # Fallback: strip 'package' keyword from raw text
            text = _node_text(child, src)
            return text.removeprefix("package").strip()
    return ""


def _get_visibility(node: TSNode, src: bytes) -> str:
    for child in node.children:
        if child.type == "modifiers":
            text = _node_text(child, src)
            if "public" in text:
                return "public"
            if "private" in text:
                return "private"
            if "protected" in text:
                return "protected"
            if "internal" in text:
                return "internal"
    return "public"


class KotlinFileParser:
    def __init__(self, file_path: str, src: bytes):
        self.file_path = file_path
        self.src = src
        self.package = ""
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []

    def _add_node(self, node: Node):
        self.nodes.append(node)

    def _add_edge(self, source_id: str, target_id: str, etype: EdgeType, meta=None):
        eid = _uid(source_id, target_id, etype.value)
        self.edges.append(Edge(id=eid, source_id=source_id, target_id=target_id,
                               type=etype, metadata=meta or {}))

    def _get_node(self, nid: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == nid), None)

    # ------------------------------------------------------------------ #
    def parse(self, root: TSNode):
        self.package = _get_package(root, self.src)
        for child in root.children:
            if child.type == "class_declaration":
                self._parse_class(child, parent_id=None)
            elif child.type == "function_declaration":
                self._parse_function(child, parent_id=None)
            elif child.type == "property_declaration":
                self._parse_property(child, parent_id=None)

    # ------------------------------------------------------------------ #
    def _parse_class(self, node: TSNode, parent_id: Optional[str]):
        # Determine kind: class / interface / object / enum class
        kind = "class"
        is_abstract = False
        for child in node.children:
            if child.type == "interface":
                kind = "interface"
            if child.type == "modifiers":
                mod_text = _node_text(child, self.src)
                if "abstract" in mod_text:
                    is_abstract = True
                if "enum" in mod_text:
                    kind = "enum"
            if child.type == "object":
                kind = "object"

        # Name — tree-sitter-kotlin uses 'identifier' (not 'type_identifier') for class names
        name = ""
        for child in node.children:
            if child.type in ("type_identifier", "identifier"):
                name = _node_text(child, self.src)
                break
        if not name:
            return

        qname = f"{self.package}.{name}" if self.package else name

        if kind == "interface":
            ntype = NodeType.INTERFACE
        elif kind == "enum":
            ntype = NodeType.ENUM
        elif kind == "object":
            ntype = NodeType.OBJECT
        elif is_abstract:
            ntype = NodeType.ABSTRACT_CLASS
        else:
            ntype = NodeType.CLASS

        visibility = _get_visibility(node, self.src)
        nid = _uid(qname, self.file_path)
        n = Node(
            id=nid, type=ntype, name=name, qualified_name=qname,
            file_path=self.file_path, line_number=node.start_point[0] + 1,
            package_name=self.package, language="kotlin",
            is_abstract=is_abstract, visibility=visibility,
        )
        self._add_node(n)

        if parent_id:
            self._add_edge(parent_id, nid, EdgeType.CONTAINS)

        # --- Delegation specifiers (superclass / interfaces) ---
        for child in node.children:
            if child.type == "delegation_specifiers":
                self._parse_delegation(child, nid)

        # --- Body ---
        for child in node.children:
            if child.type == "class_body":
                self._parse_class_body(child, nid)
            elif child.type == "enum_class_body":
                self._parse_class_body(child, nid)

    def _parse_delegation(self, node: TSNode, class_id: str):
        """Extract superclass and implemented interfaces from delegation_specifiers."""
        # Each child is either a constructor_invocation (class extends) or a
        # user_type / type_identifier (interface implements)
        for child in node.children:
            if child.type in (",",):
                continue
            self._collect_type_refs(child, class_id)

    def _collect_type_refs(self, node: TSNode, class_id: str):
        # tree-sitter-kotlin uses 'type_identifier' OR plain 'identifier' for type names
        if node.type in ("type_identifier", "identifier") and node.parent and node.parent.type not in (
            "function_declaration", "property_declaration", "variable_declaration",
            "simple_identifier",
        ):
            type_name = _node_text(node, self.src).strip()
            if not type_name or type_name in (":", ",", "(", ")"):
                return
            tid = _uid(type_name, "type_ref")
            if not self._get_node(tid):
                self.nodes.append(Node(id=tid, type=NodeType.CLASS, name=type_name,
                                       qualified_name=type_name, language="kotlin"))
            android_base = any(type_name.endswith(s) for s in
                               ("Activity", "Fragment", "ViewModel", "Service",
                                "Receiver", "Provider", "Application", "View",
                                "Adapter", "ViewHolder", "Dialog", "Worker"))
            etype = EdgeType.EXTENDS if android_base else EdgeType.IMPLEMENTS
            self._add_edge(class_id, tid, etype)
        else:
            for child in node.children:
                self._collect_type_refs(child, class_id)

    def _parse_class_body(self, body: TSNode, parent_id: str):
        for child in body.children:
            if child.type == "class_declaration":
                self._parse_class(child, parent_id)
            elif child.type == "function_declaration":
                self._parse_function(child, parent_id)
            elif child.type == "property_declaration":
                self._parse_property(child, parent_id)
            elif child.type == "companion_object":
                self._parse_companion(child, parent_id)

    def _parse_companion(self, node: TSNode, parent_id: str):
        parent = self._get_node(parent_id)
        comp_name = f"{parent.name if parent else 'Unknown'}.Companion"
        qname = f"{parent.qualified_name}.Companion" if parent else comp_name
        nid = _uid(qname, self.file_path)
        n = Node(
            id=nid, type=NodeType.OBJECT, name="Companion", qualified_name=qname,
            file_path=self.file_path, line_number=node.start_point[0] + 1,
            package_name=self.package, language="kotlin",
        )
        self._add_node(n)
        self._add_edge(parent_id, nid, EdgeType.CONTAINS)
        for child in node.children:
            if child.type == "class_body":
                self._parse_class_body(child, nid)

    def _parse_function(self, node: TSNode, parent_id: Optional[str]):
        name = ""
        for child in node.children:
            # tree-sitter-kotlin uses 'simple_identifier' OR 'identifier' for function names
            if child.type in ("simple_identifier", "identifier"):
                name = _node_text(child, self.src)
                break
        if not name:
            return

        parent = self._get_node(parent_id) if parent_id else None
        qname = f"{parent.qualified_name}.{name}" if parent else name
        visibility = _get_visibility(node, self.src)
        fid = _uid(qname, self.file_path, node.start_point[0])
        f = Node(
            id=fid, type=NodeType.METHOD, name=name, qualified_name=qname,
            file_path=self.file_path, line_number=node.start_point[0] + 1,
            package_name=self.package, language="kotlin", visibility=visibility,
        )
        self._add_node(f)
        if parent_id:
            self._add_edge(parent_id, fid, EdgeType.CONTAINS)

        # Collect calls inside function body
        for child in node.children:
            if child.type == "function_body":
                self._collect_calls(child, fid)

    def _parse_property(self, node: TSNode, parent_id: Optional[str]):
        name = ""
        for child in node.children:
            if child.type == "variable_declaration":
                for sub in child.children:
                    if sub.type in ("simple_identifier", "identifier"):
                        name = _node_text(sub, self.src)
                        break
            elif child.type in ("simple_identifier", "identifier") and not name:
                # Fallback: some property_declarations don't have variable_declaration
                name = _node_text(child, self.src)
            if name:
                break
        if not name:
            return

        parent = self._get_node(parent_id) if parent_id else None
        qname = f"{parent.qualified_name}.{name}" if parent else name
        visibility = _get_visibility(node, self.src)
        pid = _uid(qname, self.file_path, node.start_point[0])
        p = Node(
            id=pid, type=NodeType.PROPERTY, name=name, qualified_name=qname,
            file_path=self.file_path, line_number=node.start_point[0] + 1,
            package_name=self.package, language="kotlin", visibility=visibility,
        )
        self._add_node(p)
        if parent_id:
            self._add_edge(parent_id, pid, EdgeType.CONTAINS)

    def _collect_calls(self, node: TSNode, caller_id: str):
        if node.type == "call_expression":
            # Try to get the name being called
            first = node.children[0] if node.children else None
            if first:
                callee_name = ""
                if first.type in ("simple_identifier", "identifier"):
                    callee_name = _node_text(first, self.src)
                elif first.type == "navigation_expression":
                    # e.g. viewModel.someMethod() — get last identifier
                    for sub in reversed(first.children):
                        if sub.type in ("simple_identifier", "identifier"):
                            callee_name = _node_text(sub, self.src)
                            break
                if callee_name:
                    cid = _uid(callee_name, "method_ref")
                    if not self._get_node(cid):
                        self.nodes.append(Node(id=cid, type=NodeType.METHOD,
                                               name=callee_name, qualified_name=callee_name,
                                               language="kotlin"))
                    self._add_edge(caller_id, cid, EdgeType.CALLS,
                                   {"line": node.start_point[0] + 1})
        for child in node.children:
            self._collect_calls(child, caller_id)


def parse_kotlin_file(file_path: str) -> Tuple[List[Node], List[Edge]]:
    src = Path(file_path).read_bytes()
    tree = _parser.parse(src)
    fp = KotlinFileParser(file_path, src)
    fp.parse(tree.root_node)

    # Simple intra-file method call resolution
    concrete_methods = {n.name: n.id for n in fp.nodes if n.type == NodeType.METHOD and n.file_path}
    method_refs = {n.id: n for n in fp.nodes if n.type == NodeType.METHOD and not n.file_path}

    for edge in fp.edges:
        if edge.type == EdgeType.CALLS and edge.target_id in method_refs:
            ref_name = method_refs[edge.target_id].name
            if ref_name in concrete_methods:
                edge.target_id = concrete_methods[ref_name]

    # Remove unreferenced method_refs to keep graph clean
    used_nodes = {e.target_id for e in fp.edges} | {e.source_id for e in fp.edges}
    fp.nodes = [n for n in fp.nodes if n.file_path or n.id in used_nodes]

    return fp.nodes, fp.edges
