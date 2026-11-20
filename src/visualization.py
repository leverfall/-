"""Graphviz DOT serialization and standalone SVG graph visualization."""

from collections import deque
from html import escape
from pathlib import Path
import shutil
import subprocess


class VisualizationError(Exception):
    """Raised when the graph cannot be saved."""


def graph_to_dot(graph):
    """Serialize dependencies in Graphviz DOT format, including isolated nodes."""
    lines = ["digraph dependencies {", "    rankdir=LR;", "    node [shape=box, style=rounded];"]
    for name in graph:
        lines.append(f'    "{_quote(name)}";')
    for name, dependencies in graph.items():
        for child in dependencies:
            lines.append(f'    "{_quote(name)}" -> "{_quote(child)}";')
    return "\n".join([*lines, "}", ""])


def _quote(value):
    """Escape DOT quoted identifier text."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _levels(graph):
    """Place reachable nodes at their minimum BFS depth without recursion."""
    levels = {}
    if not graph:
        return levels
    root = next(iter(graph))
    queue = deque([(root, 0)])
    while queue:
        name, level = queue.popleft()
        if name in levels:
            continue
        levels[name] = level
        for child in graph.get(name, ()):
            if child not in levels:
                queue.append((child, level + 1))
    for name in graph:
        levels.setdefault(name, 0)
    return levels


def _fallback_svg(graph):
    """Render a valid small SVG without optional system dependencies."""
    levels = _levels(graph)
    columns = {}
    for name, level in levels.items():
        columns.setdefault(level, []).append(name)
    width = max(350, (max(columns, default=0) + 1) * 200 + 60)
    height = max(160, max((len(col) for col in columns.values()), default=1) * 95 + 60)
    positions = {}
    for level, names in columns.items():
        for index, name in enumerate(names):
            positions[name] = (level * 200 + 100, index * 95 + 80)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="7" '
        'refX="8" refY="3.5" orient="auto">'
        '<polygon points="0 0,9 3.5,0 7" fill="#64748b"/>'
        '</marker></defs>',
    ]
    for name, children in graph.items():
        x1, y1 = positions[name]
        for child in children:
            if child not in positions:
                continue
            x2, y2 = positions[child]
            if x1 == x2 and y1 == y2:
                path = f'M {x1+40} {y1} C {x1+120} {y1-85}, {x1-120} {y1-85}, {x1-40} {y1}'
            else:
                path = (f'M {x1+40} {y1} C {x1+95} {y1}, '
                        f'{x2-95} {y2}, {x2-43} {y2}')
            parts.append(f'<path d="{path}" fill="none" stroke="#64748b" '
                         'stroke-width="1.5" marker-end="url(#arrow)"/>')
    for name, (x, y) in positions.items():
        parts.append(f'<rect x="{x-40}" y="{y-18}" width="80" height="36" '
                     'rx="6" fill="#eff6ff" stroke="#2563eb"/>')
        parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" '
                     'font-family="Arial,sans-serif" font-size="14" '
                     f'fill="#0f172a">{escape(name)}</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def save_graph(graph, svg_path):
    """Save DOT beside SVG, rendering with Graphviz or portable fallback."""
    svg = Path(svg_path)
    dot = svg.with_suffix('.dot')
    if not svg.parent.is_dir():
        raise VisualizationError(f'папка для результата не найдена: {svg.parent}')
    try:
        dot.write_text(graph_to_dot(graph), encoding='utf-8')
        dot_command = shutil.which('dot')
        if dot_command:
            subprocess.run(
                [dot_command, '-Tsvg', str(dot), '-o', str(svg)],
                capture_output=True, text=True, check=True,
            )
            method = 'Graphviz dot'
        else:
            svg.write_text(_fallback_svg(graph), encoding='utf-8')
            method = 'встроенный SVG-рендерер'
    except (OSError, subprocess.CalledProcessError) as error:
        raise VisualizationError(f'не удалось сохранить граф: {error}') from error
    return dot, svg, method
