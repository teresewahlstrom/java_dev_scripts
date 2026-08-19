#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
import re

# match fenced code blocks with optional language (e.g. ```mermaid or ```plaintext)
MERMAID_BLOCK_RE = re.compile(r"```(?:mermaid|[\w+-]+)?\s*(.*?)```", re.DOTALL)
NODE_ID_RE = re.compile(r"^\s*([A-Za-z0-9_]+)")
NODE_LABEL_RE = re.compile(r"([A-Za-z0-9_]+)\s*(\[[^\]]*\]|\{[^}]*\}|\([^)]*\))")
EDGE_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*--?>\s*(?:\|([^|]*)\|\s*)?([A-Za-z0-9_]+)")


def extract_mermaid(markdown: str) -> str | None:
    # If the file itself starts with mermaid content (no fenced block), accept it
    if markdown.lstrip().lower().startswith(("flowchart", "graph", "sequence")):
        return markdown.strip()
    # Prefer explicitly labelled mermaid block
    explicit = re.search(r"```mermaid\s*(.*?)```", markdown, re.DOTALL)
    if explicit:
        return explicit.group(1).strip()

    # Fallback: find any fenced code block and return it if it looks like a mermaid flowchart
    for m in MERMAID_BLOCK_RE.finditer(markdown):
        content = m.group(1).strip()
        # consider it mermaid if it starts with 'flowchart' or 'graph' or 'sequence'
        if content.lstrip().lower().startswith(("flowchart", "graph", "sequence")):
            return content

    return None


def parse_mermaid_flowchart(block: str):
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    # skip leading 'flowchart TD' or similar
    if lines and lines[0].lower().startswith("flowchart"):
        direction = lines[0].split()[1] if len(lines[0].split()) > 1 else "TD"
        lines = lines[1:]
    else:
        direction = "TD"

    nodes: dict[str, dict] = {}
    edges: list[tuple[str, str, str]] = []  # (src, label, dst)

    def record_node(token: str, token_with_label: str | None):
        if token in nodes:
            return
        label = token
        shape = "box"
        if token_with_label:
            m = NODE_LABEL_RE.match(token_with_label)
            if m:
                tok = m.group(1)
                lbl_raw = m.group(2)
                # label inside [] or {} or ()
                lbl = lbl_raw[1:-1]
                lbl = lbl.replace('<br/>', '\\n')
                label = lbl
                if lbl_raw.startswith("{") and lbl_raw.endswith("}"):
                    shape = "diamond"
                elif lbl_raw.startswith("(") and lbl_raw.endswith(")"):
                    shape = "ellipse"
                else:
                    shape = "box"
        nodes[token] = {"label": label, "shape": shape}

    # First pass: capture explicit node label occurrences in lines
    for line in lines:
        # find occurrences like A[Label] or B{Label}
        for m in NODE_LABEL_RE.finditer(line):
            token = m.group(1)
            token_with_label = m.group(0)
            record_node(token, token_with_label)

    # Second pass: parse edges
    for line in lines:
        em = EDGE_RE.match(line)
        if em:
            src = em.group(1)
            label = em.group(2) or ""
            dst = em.group(3)
            # find node label tokens in the line to enrich nodes dict
            for m in NODE_LABEL_RE.finditer(line):
                record_node(m.group(1), m.group(0))
            # ensure nodes exist even if not labeled elsewhere
            if src not in nodes:
                record_node(src, None)
            if dst not in nodes:
                record_node(dst, None)
            edges.append((src, label.strip(), dst))
        else:
            # ignore non-edge lines
            continue

    return direction, nodes, edges


def generate_dot_from_parsed(direction: str, nodes: dict, edges: list[tuple[str, str, str]], rankdir: str = "TB", dpi: int | None = None, dark: bool = False) -> str:
    lines = []
    lines.append("digraph mermaid_flowchart {")
    lines.append(f"  rankdir={rankdir};")
    if dark:
        lines.append('  graph [bgcolor="#111111"];')
        lines.append('  node [style=filled, fillcolor="#2b2b2b", fontcolor="#e6e6e6"];')
        lines.append('  edge [color="#8a8a8a", fontcolor="#e6e6e6"];')
    else:
        lines.append('  node [shape=box];')

    if dpi:
        lines.append(f'  graph [dpi={dpi}];')

    lines.append("")

    for src, label, dst in edges:
        if label:
            # quote label
            lines.append(f'  "{src}" -> "{dst}" [label="{label}"];')
        else:
            lines.append(f'  "{src}" -> "{dst}";')

    lines.append("")

    for node, info in nodes.items():
        lbl = info["label"].replace('"', '\\"')
        shape = info.get("shape", "box")
        if dark:
            lines.append(f'  "{node}" [label="{lbl}", shape={shape}, fontcolor="#e6e6e6", style=filled, fillcolor="#2b2b2b"];')
        else:
            lines.append(f'  "{node}" [label="{lbl}", shape={shape}];')

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def render_graph(dot_path: Path, dpi: int | None = None) -> None:
    dot_executable = shutil.which("dot")
    if not dot_executable:
        raise SystemExit("Graphviz 'dot' executable not found in PATH.")

    out_svg = dot_path.with_suffix(".svg")
    out_png = dot_path.with_suffix(".png")

    cmd = [dot_executable, "-Tsvg", str(dot_path), "-o", str(out_svg)]
    if dpi:
        cmd.insert(1, f"-Gdpi={dpi}")
    subprocess.run(cmd, check=True)
    cmd2 = [dot_executable, "-Tpng", str(dot_path), "-o", str(out_png)]
    if dpi:
        cmd2.insert(1, f"-Gdpi={dpi}")
    subprocess.run(cmd2, check=True)

    print(f"Wrote {out_svg}")
    print(f"Wrote {out_png}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract first mermaid flowchart from a markdown file and render DOT/SVG/PNG.")
    parser.add_argument("--md", default="report/assignment/5_games_study/klassificering_vinstsystem_1.md", help="Markdown file with mermaid block")
    parser.add_argument("--out", default="report/code_visualization/mermaid_flowchart.dot", help="Output DOT path")
    parser.add_argument("--no-render", action="store_true", help="Only write DOT file; skip SVG/PNG rendering")
    parser.add_argument("--rankdir", choices=["TB", "LR"], default="TB", help="Graph direction")
    parser.add_argument("--dpi", type=int, help="DPI for rendering (e.g. 300)")
    parser.add_argument("--dark", action="store_true", help="Use dark theme for DOT output")
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        raise SystemExit(f"Markdown file not found: {md_path}")

    text = md_path.read_text(encoding="utf-8")
    mermaid = extract_mermaid(text)
    if not mermaid:
        raise SystemExit("No mermaid block found in the markdown file.")

    direction, nodes, edges = parse_mermaid_flowchart(mermaid)
    rankdir = args.rankdir if args.rankdir else ("LR" if direction.upper().endswith("LR") else "TB")

    dot_content = generate_dot_from_parsed(direction, nodes, edges, rankdir=rankdir, dpi=args.dpi, dark=args.dark)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dot_content, encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_render:
        render_graph(out_path, dpi=args.dpi)


if __name__ == "__main__":
    main()
