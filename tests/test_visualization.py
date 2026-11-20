"""Unit tests for Graphviz DOT and SVG export."""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from src.visualization import (
    VisualizationError, graph_to_dot, save_graph,
)


class VisualizationTests(unittest.TestCase):
    """Check directed edges, isolated nodes and both SVG renderers."""

    def setUp(self):
        self.graph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}

    def test_dot_header_and_edges(self):
        dot = graph_to_dot(self.graph)
        self.assertIn('digraph dependencies {', dot)
        self.assertIn('"A" -> "B";', dot)
        self.assertIn('"C" -> "D";', dot)

    def test_dot_isolated_node(self):
        self.assertIn('"A";', graph_to_dot({'A': []}))

    def test_dot_cycle(self):
        dot = graph_to_dot({'A': ['B'], 'B': ['A']})
        self.assertIn('"B" -> "A";', dot)

    def test_save_svg_with_graphviz_when_available(self):
        with tempfile.TemporaryDirectory() as folder:
            svg = Path(folder) / 'graph.svg'
            _, result, _ = save_graph(self.graph, svg)
            self.assertTrue(result.is_file())
            self.assertTrue(svg.with_suffix('.dot').is_file())
            self.assertTrue(ET.parse(svg).getroot().tag.endswith('svg'))

    def test_fallback_without_dot(self):
        with tempfile.TemporaryDirectory() as folder:
            svg = Path(folder) / 'graph.svg'
            with patch('src.visualization.shutil.which', return_value=None):
                _, _, method = save_graph(self.graph, svg)
            self.assertIn('встроенный', method)
            self.assertTrue(ET.parse(svg).getroot().tag.endswith('svg'))
            self.assertIn('>A</text>', svg.read_text(encoding='utf-8'))

    def test_fallback_for_cycle(self):
        with tempfile.TemporaryDirectory() as folder:
            svg = Path(folder) / 'cycle.svg'
            with patch('src.visualization.shutil.which', return_value=None):
                save_graph({'A': ['B'], 'B': ['A']}, svg)
            ET.parse(svg)

    def test_three_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('A', 'B', 'C'):
                with patch('src.visualization.shutil.which', return_value=None):
                    save_graph({name: self.graph[name]}, Path(folder) / f'{name}.svg')
                self.assertTrue((Path(folder) / f'{name}.svg').exists())

    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(VisualizationError):
                save_graph(self.graph, Path(folder) / 'missing' / 'graph.svg')


if __name__ == '__main__':
    unittest.main()
