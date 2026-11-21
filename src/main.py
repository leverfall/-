"""CLI for Ubuntu APT dependency graphs and load ordering (stages 1–5)."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

from src.apt_repository import RepositoryError
from src.dependency_graph import bfs_graph, read_apt_graph, read_test_graph
from src.load_order import dependency_load_order
from src.visualization import VisualizationError, save_graph


PACKAGE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
TEST_PACKAGE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z]*$")
VERSION_PATTERN = re.compile(r"^[0-9][A-Za-z0-9.+:~\-]*$")
MAX_UNRESOLVED_DETAILS = 10


def package_name(value):
    """Validate a Debian/Ubuntu package name."""
    if not PACKAGE_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "имя пакета должно начинаться с маленькой буквы или цифры "
            "и содержать только a-z, 0-9, +, . или -"
        )
    return value


def validate_package(value, test_mode, parser):
    """Allow uppercase letters in test mode, Debian names otherwise."""
    if test_mode:
        if not TEST_PACKAGE_PATTERN.fullmatch(value):
            parser.error(
                "в тестовом режиме имя пакета должно состоять "
                "из латинских букв"
            )
    else:
        try:
            package_name(value)
        except argparse.ArgumentTypeError as error:
            parser.error(str(error))


def package_version(value):
    """Validate the basic shape of a Debian package version."""
    if not VERSION_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "версия должна начинаться с цифры и содержать только "
            "буквы, цифры и символы . + : ~ -"
        )
    return value


def output_name(value):
    """Require a file path with an SVG extension."""
    path = Path(value)
    if not path.name or path.suffix.lower() != ".svg":
        raise argparse.ArgumentTypeError(
            "имя файла должно заканчиваться на .svg"
        )
    if path.exists() and path.is_dir():
        raise argparse.ArgumentTypeError("выходной путь является папкой")
    return value


def validate_source(source, test_mode, parser):
    """Validate the selected repository source for the selected mode."""
    if test_mode:
        path = Path(source)
        if not path.is_file():
            parser.error("в тестовом режиме --source должен указывать на файл")
        try:
            with path.open("r", encoding="utf-8") as handle:
                handle.read(1)
        except (OSError, UnicodeError) as error:
            parser.error(f"невозможно прочитать тестовый файл: {error}")
        return

    parsed = urlparse(source)
    if (parsed.scheme not in ("http", "https")
            or not parsed.netloc or parsed.username or parsed.password):
        parser.error("--source должен быть корректным HTTP(S) URL")
    if parsed.query or parsed.fragment:
        parser.error("URL репозитория не должен содержать ? или #")


def build_parser():
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Анализатор зависимостей Ubuntu APT (этап 5)"
    )
    parser.add_argument(
        "--package", required=True,
        help="имя пакета, например bash"
    )
    parser.add_argument(
        "--source", required=True,
        help="HTTP(S) URL репозитория или путь к тестовому файлу"
    )
    parser.add_argument(
        "--test-mode", action="store_true",
        help="использовать локальный тестовый файл вместо URL"
    )
    parser.add_argument(
        "--version", required=True, type=package_version,
        help="версия пакета, например 5.2.21-2ubuntu4"
    )
    parser.add_argument(
        "--output", required=True, type=output_name,
        help="имя будущего SVG-изображения"
    )
    parser.add_argument(
        "--load-order", action="store_true",
        help="вывести порядок загрузки (зависимости перед пакетом)"
    )
    return parser


def _load_repository(args):
    """Choose the test graph or an Ubuntu APT index graph."""
    if args.test_mode:
        return read_test_graph(args.source), args.package.upper(), []
    graph, missing = read_apt_graph(
        args.source, args.package, args.version
    )
    return graph, args.package, missing


def _show_bfs(graph, order):
    """Print reachable dependencies and BFS traversal order."""
    print("\nГраф зависимостей (BFS):")
    for name, dependencies in graph.items():
        print(f"  {name}: {' '.join(dependencies) or '(нет)'}")
    print("Порядок обхода BFS: " + " -> ".join(order))


def _show_load_order(graph):
    """Print dependency-first ordering or describe a cycle."""
    try:
        loading = dependency_load_order(graph)
    except RepositoryError as error:
        print(f"Порядок загрузки недоступен: {error}")
    else:
        print("Порядок загрузки: " + " -> ".join(loading))


def _show_unresolved(unresolved, graph):
    """Show missing index dependency groups for reachable packages."""
    visible = [
        item for item in unresolved
        if item.split(": ", 1)[0] in graph
    ]
    if not visible:
        return
    print("\nПримечание: часть зависимостей не найдена в индексе:")
    for item in visible[:MAX_UNRESOLVED_DETAILS]:
        print(f"  - {item}")
    if len(visible) > MAX_UNRESOLVED_DETAILS:
        print(f"  ... и ещё {len(visible) - MAX_UNRESOLVED_DETAILS}")


def main(argv=None):
    """Validate CLI input, analyze dependencies and save the graph."""
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_package(args.package, args.test_mode, parser)
    validate_source(args.source, args.test_mode, parser)
    print(f"package: {args.package}")
    print(f"source: {args.source}")
    print(f"test_mode: {args.test_mode}")
    print(f"version: {args.version}")
    print(f"output: {args.output}")
    try:
        repository, package, unresolved = _load_repository(args)
        graph, order = bfs_graph(repository, package)
    except RepositoryError as error:
        parser.exit(1, f"Ошибка: {error}\n")
    _show_bfs(graph, order)
    if args.load_order:
        _show_load_order(graph)
    try:
        dot_file, svg_file, renderer = save_graph(graph, args.output)
    except VisualizationError as error:
        parser.exit(1, f"Ошибка визуализации: {error}\n")
    print(f"Graphviz DOT: {dot_file}")
    print(f"SVG: {svg_file} ({renderer})")
    _show_unresolved(unresolved, graph)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
