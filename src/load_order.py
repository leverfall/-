"""Determine a deterministic dependency-first order without recursion."""

from heapq import heappop, heappush

from src.apt_repository import RepositoryError


def dependency_load_order(graph):
    """Topologically order a dependency graph, dependencies before users.

    An edge A -> B means A depends on B. A cycle makes a valid
    topological ordering impossible and is reported explicitly.
    """
    pending = {name: len(set(deps)) for name, deps in graph.items()}
    dependents = {name: [] for name in graph}
    for name, dependencies in graph.items():
        for dependency in set(dependencies):
            if dependency not in graph:
                raise RepositoryError(
                    f"нет описания зависимости {dependency!r} пакета {name!r}"
                )
            dependents[dependency].append(name)
    ready = []
    for name, count in pending.items():
        if count == 0:
            heappush(ready, name)
    order = []
    while ready:
        name = heappop(ready)
        order.append(name)
        for dependent in dependents[name]:
            pending[dependent] -= 1
            if pending[dependent] == 0:
                heappush(ready, dependent)
    if len(order) != len(graph):
        remaining = sorted(name for name, count in pending.items() if count)
        raise RepositoryError(
            "невозможно определить порядок загрузки: "
            "граф содержит цикл зависимостей (" + ", ".join(remaining) + ")"
        )
    return order
