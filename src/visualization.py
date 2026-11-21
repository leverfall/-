"""Graphviz DOT serialization and standalone SVG graph visualization."""

from collections import deque
from html import escape
from pathlib import Path
import shutil
import subprocess


NODE_WIDTH = 80
NODE_HEIGHT = 36
COLUMN_STEP = 200
ROW_STEP = 95
SVG_MARGIN = 60


class VisualizationError(Exception):
    """Raised when the graph cannot be saved."""


def graph_to_dot(graph):
    """Serialize dependency edges and isolated nodes into DOT format."""
    lines = [
        "digraph dependencies {",
        "    rankdir=LR;",
        "    node [shape=box, style=rounded];",
    ]
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


def _svg_layout(graph):
    """Calculate SVG canvas dimensions and node centers."""
    columns = {}
    for name, level in _levels(graph).items():
        columns.setdefault(level, []).append(name)
    max_rows = max((len(col) for col in columns.values()), default=1)
    width = max(350, (max(columns, default=0) + 1) * COLUMN_STEP)
    width += SVG_MARGIN
    height = max(160, max_rows * ROW_STEP + SVG_MARGIN)
    positions = {}
    for level, names in columns.items():
        for index, name in enumerate(names):
            positions[name] = (
                level * COLUMN_STEP + 100,
                index * ROW_STEP + 80,
            )
    return width, height, positions


def _svg_header(width, height):
    """Prepare SVG root, background and arrow marker."""
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="7" '
        'refX="8" refY="3.5" orient="auto">'
        '<polygon points="0 0,9 3.5,0 7" fill="#64748b"/>'
        '</marker></defs>',
    ]


def _svg_path(x1, y1, x2, y2):
    """Generate a cubic path for one dependency arrow."""
    if x1 == x2 and y1 == y2:
        return (
            f'M {x1+40} {y1} C {x1+120} {y1-85}, '
            f'{x1-120} {y1-85}, {x1-40} {y1}'
        )
    return (
        f'M {x1+40} {y1} C {x1+95} {y1}, '
        f'{x2-95} {y2}, {x2-43} {y2}'
    )


def _svg_edges(graph, positions):
    """Draw each dependency arrow between positioned graph nodes."""
    parts = []
    for name, children in graph.items():
        x1, y1 = positions[name]
        for child in children:
            if child not in positions:
                continue
            x2, y2 = positions[child]
            path = _svg_path(x1, y1, x2, y2)
            parts.append(
                f'<path d="{path}" fill="none" stroke="#64748b" '
                'stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
    return parts


def _svg_nodes(positions):
    """Draw labelled boxes for each package."""
    parts = []
    for name, (x, y) in positions.items():
        parts.append(
            f'<rect x="{x-40}" y="{y-18}" width="{NODE_WIDTH}" '
            f'height="{NODE_HEIGHT}" rx="6" '
            'fill="#eff6ff" stroke="#2563eb"/>'
        )
        parts.append(
            f'<text x="{x}" y="{y+5}" text-anchor="middle" '
            'font-family="Arial,sans-serif" font-size="14" '
            f'fill="#0f172a">{escape(name)}</text>'
        )
    return parts


def _fallback_svg(graph):
    """Render a valid small SVG without optional system dependencies."""
    width, height, positions = _svg_layout(graph)
    parts = _svg_header(width, height)
    parts.extend(_svg_edges(graph, positions))
    parts.extend(_svg_nodes(positions))
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def save_graph(graph, svg_path):
    """Save DOT beside SVG, rendering with Graphviz or portable fallback."""
    svg = Path(svg_path)
    dot = svg.with_suffix('.dot')
    if not svg.parent.is_dir():
        raise VisualizationError(
            f'папка для результата не найдена: {svg.parent}'
        )
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
        raise VisualizationError(
            f'не удалось сохранить граф: {error}'
        ) from error
    return dot, svg, method
