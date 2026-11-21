"""Build reachable directed dependency graphs by iterative BFS."""

from collections import deque
import re

from src.apt_repository import RepositoryError, fetch_index, parse_stanzas


TEST_NAME = re.compile(r"^[A-Z]+$")
APT_NAME = re.compile(r"^([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9]+)?")


def _parse_test_line(original, number):
    """Validate a meaningful test line and parse its adjacency list."""
    line = original.strip()
    if not line or line.startswith("#"):
        return None
    if ":" not in line:
        raise RepositoryError(f"строка {number}: ожидается A: B C")
    name, raw = line.split(":", 1)
    name = name.strip()
    children = raw.split()
    if not TEST_NAME.fullmatch(name) or any(
        not TEST_NAME.fullmatch(child) for child in children
    ):
        raise RepositoryError(
            f"строка {number}: требуются большие латинские буквы A-Z"
        )
    return name, list(dict.fromkeys(children))


def _check_test_links(graph):
    """Reject references to missing test packages."""
    for name, children in graph.items():
        for child in children:
            if child not in graph:
                raise RepositoryError(
                    f"зависимость {child} пакета {name} не описана в файле"
                )


def read_test_graph(path):
    """Read an entire test graph; require uppercase Latin package names."""
    from pathlib import Path

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RepositoryError(f"ошибка тестового файла: {error}") from error
    graph = {}
    for number, original in enumerate(lines, 1):
        parsed = _parse_test_line(original, number)
        if parsed is None:
            continue
        name, children = parsed
        if name in graph:
            raise RepositoryError(
                f"строка {number}: повторное описание {name}"
            )
        graph[name] = children
    _check_test_links(graph)
    return graph


def _read_apt_records(source, root, version):
    """Collect index records, retaining the exact requested root version."""
    records = {}
    root_record = None
    for record in parse_stanzas(fetch_index(source)):
        name = record.get("Package")
        if not name:
            continue
        records.setdefault(name, record)
        if name == root and record.get("Version") == version:
            root_record = record
    if root_record is None:
        raise RepositoryError(f"пакет {root!r} версии {version!r} не найден")
    records[root] = root_record
    return records


def _apt_alternatives(expression):
    """Extract valid alternative package names from a dependency group."""
    alternatives = []
    for option in expression.split("|"):
        match = APT_NAME.match(option.strip())
        if match:
            alternatives.append(match.group(1))
    return alternatives


def _record_dependencies(name, record, records):
    """Resolve known index dependencies, reporting unresolved groups."""
    from src.apt_repository import split_dependencies

    fields = (record.get("Pre-Depends", ""), record.get("Depends", ""))
    raw = ", ".join(filter(None, fields))
    children = []
    unresolved = []
    for item in split_dependencies(raw):
        selected = next(
            (option for option in _apt_alternatives(item) if option in records),
            None,
        )
        if selected:
            children.append(selected)
        else:
            unresolved.append(f"{name}: {item}")
    return list(dict.fromkeys(children)), unresolved


def read_apt_graph(source, root, version):
    """Build APT index adjacency; no full dependency-version solver."""
    records = _read_apt_records(source, root, version)
    graph = {}
    unresolved = set()
    for name, record in records.items():
        children, missing = _record_dependencies(name, record, records)
        graph[name] = children
        unresolved.update(missing)
    return graph, sorted(unresolved)

def bfs_graph(repository, root):
    """Return reachable adjacency and visit order without recursive calls."""
    if root not in repository:
        raise RepositoryError(f"пакет {root!r} не найден в репозитории")
    visited = {root}
    queue = deque([root])
    result = {}
    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        result[current] = list(repository[current])
        for dependency in repository[current]:
            if dependency not in repository:
                raise RepositoryError(
                    f"для зависимости {dependency!r} нет записи в репозитории"
                )
            if dependency not in visited:
                visited.add(dependency)
                queue.append(dependency)
    return result, order
