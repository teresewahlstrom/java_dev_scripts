#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;")
IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+)\s*;")
QUALIFIED_TYPE_USAGE_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\.")


@dataclass(frozen=True)
class JavaFile:
    path: Path
    package: str | None
    fqcn: str
    node: str


def to_node_label(src_root: Path, java_file: Path) -> str:
    rel = java_file.relative_to(src_root).as_posix()
    return rel


def parse_java_file(src_root: Path, file_path: Path) -> tuple[JavaFile, list[str]]:
    lines = file_path.read_text(encoding="utf-8").splitlines()

    package: str | None = None
    imports: list[str] = []

    for line in lines:
        package_match = PACKAGE_RE.match(line)
        if package_match:
            package = package_match.group(1)
            continue

        import_match = IMPORT_RE.match(line)
        if import_match:
            imports.append(import_match.group(1))

    class_name = file_path.stem
    fqcn = f"{package}.{class_name}" if package else class_name
    java_info = JavaFile(
        path=file_path,
        package=package,
        fqcn=fqcn,
        node=to_node_label(src_root, file_path),
    )
    return java_info, imports


def resolve_import_to_fqcn(import_name: str, known_fqcns: set[str]) -> str | None:
    candidate = import_name
    while True:
        if candidate in known_fqcns:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]


def generate_dot(src_root: Path, rankdir: str = "TB", size: str | None = None, dpi: int | None = None, dark: bool = False) -> str:
    java_paths = sorted(src_root.rglob("*.java"), key=lambda p: p.as_posix())
    parsed: list[tuple[JavaFile, list[str]]] = [parse_java_file(src_root, p) for p in java_paths]

    by_fqcn = {java.fqcn: java for java, _ in parsed}
    known_fqcns = set(by_fqcn.keys())
    by_package: dict[str, dict[str, JavaFile]] = {}
    for java, _ in parsed:
        if java.package is None:
            continue
        by_package.setdefault(java.package, {})[java.path.stem] = java

    edges: set[tuple[str, str]] = set()
    nodes: set[str] = {java.node for java, _ in parsed}

    for java_file, imports in parsed:
        for import_name in imports:
            target_fqcn = resolve_import_to_fqcn(import_name, known_fqcns)
            if not target_fqcn:
                continue
            source_node = java_file.node
            target_node = by_fqcn[target_fqcn].node
            if source_node != target_node:
                edges.add((source_node, target_node))

        if java_file.package is None:
            continue

        package_members = by_package.get(java_file.package, {})
        source_text = java_file.path.read_text(encoding="utf-8")
        # remove block comments and line comments so identifiers mentioned only
        # in comments don't create spurious dependencies
        source_text_nocomments = re.sub(r"/\*.*?\*/", "", source_text, flags=re.DOTALL)
        source_text_nocomments = re.sub(r"//.*", "", source_text_nocomments)

        for type_name in set(QUALIFIED_TYPE_USAGE_RE.findall(source_text_nocomments)):
            target_java = package_members.get(type_name)
            if not target_java:
                continue
            source_node = java_file.node
            target_node = target_java.node
            if source_node != target_node:
                edges.add((source_node, target_node))

        # Also detect simple type references within the same package (e.g. field/type usage
        # like "SymbolHandlerWild" in a field declaration). The QUALIFIED_TYPE_USAGE_RE
        # detects usages such as "TypeName."; this additional check finds plain type
        # identifiers so same-package dependencies are captured in the graph.
        for type_name, target_java in package_members.items():
            # skip self-reference
            if type_name == java_file.path.stem:
                continue
            if re.search(r"\b" + re.escape(type_name) + r"\b", source_text_nocomments):
                source_node = java_file.node
                target_node = target_java.node
                if source_node != target_node:
                    edges.add((source_node, target_node))

    lines: list[str] = []
    lines.append("digraph dependencies {")
    lines.append(f"  rankdir={rankdir};")
    if dark:
        # Dark theme: dark background, muted nodes and light text
        lines.append('  graph [bgcolor="#111111"];')
        lines.append('  node [shape=box, style=filled, fillcolor="#2b2b2b", fontcolor="#e6e6e6"];')
        lines.append('  edge [color="#8a8a8a"];')
    else:
        lines.append("  node [shape=box];")

    graph_attrs: list[str] = []
    if size:
        graph_attrs.append(f'size="{size}"')
    if dpi:
        graph_attrs.append(f'dpi={dpi}')
    if graph_attrs and not dark:
        # when using dark theme, we already set graph attrs above (bgcolor); avoid duplicate graph[]
        lines.append("  graph [" + ", ".join(graph_attrs) + "];")
    lines.append("")

    for source, target in sorted(edges):
        lines.append(f'  "{source}" -> "{target}";')

    lines.append("")

    for node in sorted(nodes):
        lines.append(f'  "{node}";')

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def render_graph(dot_path: Path) -> None:
    dot_executable = shutil.which("dot")
    if not dot_executable:
        raise SystemExit("Graphviz 'dot' executable not found in PATH.")

    out_svg = dot_path.with_suffix(".svg")
    out_png = dot_path.with_suffix(".png")

    subprocess.run([dot_executable, "-Tsvg", str(dot_path), "-o", str(out_svg)], check=True)
    subprocess.run([dot_executable, "-Tpng", str(dot_path), "-o", str(out_png)], check=True)

    print(f"Wrote {out_svg}")
    print(f"Wrote {out_png}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate visualization.dot from Java imports.")
    parser.add_argument("--src", default="src/main/java", help="Path to Java source root (default: src/main/java)")
    parser.add_argument("--out", default="report/code_visualization/visualization.dot", help="Output DOT path")
    parser.add_argument("--no-render", action="store_true", help="Only write DOT file; skip SVG/PNG rendering")
    parser.add_argument("--rankdir", choices=["TB", "LR"], default="TB", help="Graph direction: TB (top-bottom) or LR (left-right)")
    parser.add_argument("--size", help="Graphviz size (width,height) e.g. '20,10' — omit to auto-size")
    parser.add_argument("--dpi", type=int, help="DPI for rendering (e.g. 300)")
    parser.add_argument("--dark", action="store_true", help="Use dark theme for DOT output (dark background)")
    args = parser.parse_args()

    src_root = Path(args.src).resolve()
    if not src_root.is_dir():
        raise SystemExit(f"Source root not found: {src_root}")

    dot_content = generate_dot(src_root, rankdir=args.rankdir, size=args.size, dpi=args.dpi, dark=args.dark)

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dot_content, encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_render:
        render_graph(out_path)


if __name__ == "__main__":
    main()
