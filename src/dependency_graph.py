"""Build reachable directed dependency graphs by iterative BFS."""

from collections import deque
import re

from src.apt_repository import RepositoryError, fetch_index, parse_stanzas


TEST_NAME = re.compile(r"^[A-Z]+$")
APT_NAME = re.compile(r"^([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9]+)?")


def read_test_graph(path):
    """Read an entire test graph; require uppercase Latin package names."""
    from pathlib import Path

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RepositoryError(f"ошибка тестового файла: {error}") from error
    graph = {}
    for number, original in enumerate(lines, 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
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
        if name in graph:
            raise RepositoryError(f"строка {number}: повторное описание {name}")
        graph[name] = list(dict.fromkeys(children))
    for name, children in graph.items():
        for child in children:
            if child not in graph:
                raise RepositoryError(
                    f"зависимость {child} пакета {name} не описана в файле"
                )
    return graph


def read_apt_graph(source, root, version):
    """Read one APT index once and select package metadata for graph traversal.

    The root version is exact. For transitive package names, the first record
    found in the given index is used, not a full APT version solver.
    """
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
    graph = {}
    unresolved = set()
    for name, record in records.items():
        raw = ", ".join(filter(None, (
            record.get("Pre-Depends", ""), record.get("Depends", "")
        )))
        from src.apt_repository import split_dependencies
        children = []
        for item in split_dependencies(raw):
            alternatives = []
            for option in item.split("|"):
                match = APT_NAME.match(option.strip())
                if match:
                    alternatives.append(match.group(1))
            selected = next((x for x in alternatives if x in records), None)
            if selected:
                children.append(selected)
            else:
                unresolved.add(f"{name}: {item}")
        graph[name] = list(dict.fromkeys(children))
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
