"""Determine a deterministic dependency-first order without recursion."""

from heapq import heappop, heappush

from src.apt_repository import RepositoryError


def _dependency_index(graph):
    """Count prerequisites and build the reverse dependency index."""
    pending = {name: len(set(deps)) for name, deps in graph.items()}
    dependents = {name: [] for name in graph}
    for name, dependencies in graph.items():
        for dependency in set(dependencies):
            if dependency not in graph:
                raise RepositoryError(
                    f"нет описания зависимости {dependency!r} "
                    f"пакета {name!r}"
                )
            dependents[dependency].append(name)
    return pending, dependents


def _topological_order(pending, dependents):
    """Apply Kahn's algorithm using a heap for deterministic ties."""
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
    return order


def dependency_load_order(graph):
    """Place dependencies before users and reject dependency cycles."""
    pending, dependents = _dependency_index(graph)
    order = _topological_order(pending, dependents)
    if len(order) != len(graph):
        remaining = sorted(name for name, count in pending.items() if count)
        raise RepositoryError(
            "невозможно определить порядок загрузки: "
            "граф содержит цикл зависимостей (" + ", ".join(remaining) + ")"
        )
    return order
