"""Read direct APT dependencies from a remote Ubuntu Packages index.

No apt executable, package manager, or third-party dependencies are used.
"""

import gzip
import io
import lzma
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
MAX_INDEX_BYTES = 160 * 1024 * 1024
DEFAULT_INDEX = "dists/noble/main/binary-amd64/Packages.xz"


class RepositoryError(Exception):
    """Describe a repository or package metadata error."""


def index_url(source):
    """Accept an exact Packages index URL or a repository base URL."""
    name = urlparse(source).path.rstrip("/").rsplit("/", 1)[-1]
    if name in ("Packages", "Packages.gz", "Packages.xz"):
        return source
    return source.rstrip("/") + "/" + DEFAULT_INDEX


def fetch_index(source):
    """Fetch and decompress an APT index with bounded memory usage."""
    url = index_url(source)
    request = Request(url, headers={"User-Agent": "apt-graph-student/1.0"})
    try:
        with urlopen(request, timeout=25) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RepositoryError(f"не удалось получить {url}: {error}") from error
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise RepositoryError("индекс репозитория слишком большой")
    try:
        if urlparse(url).path.endswith(".xz"):
            reader = lzma.LZMAFile(io.BytesIO(data))
        elif urlparse(url).path.endswith(".gz"):
            reader = gzip.GzipFile(fileobj=io.BytesIO(data))
        else:
            reader = io.BytesIO(data)
        with reader:
            raw = reader.read(MAX_INDEX_BYTES + 1)
    except (lzma.LZMAError, EOFError, OSError) as error:
        raise RepositoryError(f"повреждённый индекс пакетов: {error}") from error
    if len(raw) > MAX_INDEX_BYTES:
        raise RepositoryError("распакованный индекс слишком большой")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RepositoryError("индекс пакетов не является UTF-8") from error


def parse_stanzas(content):
    """Yield Debian control records separated by blank lines."""
    record = {}
    last_key = None
    for line in content.splitlines() + [""]:
        if not line.strip():
            if record:
                yield record
            record = {}
            last_key = None
        elif line[0].isspace():
            if last_key:
                record[last_key] += " " + line.strip()
        elif ":" in line:
            name, value = line.split(":", 1)
            record[name] = value.strip()
            last_key = name
        else:
            last_key = None


def split_dependencies(value):
    """Split comma groups, retaining alternatives and version constraints."""
    groups = []
    depth = 0
    start = 0
    for i, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            group = value[start:i].strip()
            if group:
                groups.append(group)
            start = i + 1
    last = value[start:].strip()
    if last:
        groups.append(last)
    return groups


def get_direct_dependencies(source, package, version):
    """Look up exact package/version and return Depends and Pre-Depends."""
    content = fetch_index(source)
    for record in parse_stanzas(content):
        if record.get("Package") != package:
            continue
        if record.get("Version") != version:
            continue
        dependencies = []
        for field in ("Pre-Depends", "Depends"):
            dependencies.extend(split_dependencies(record.get(field, "")))
        return dependencies
    raise RepositoryError(
        f"пакет {package!r} версии {version!r} не найден в индексе "
        f"{index_url(source)}"
    )


def get_test_dependencies(path, package):
    """Read the simple A: B C test format used by the next stage."""
    from pathlib import Path

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RepositoryError(f"ошибка тестового файла: {error}") from error
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise RepositoryError("строка тестового графа должна иметь вид A: B C")
        name, rest = line.split(":", 1)
        if name.strip().lower() == package.lower():
            return rest.split()
    raise RepositoryError(f"пакет {package!r} не найден в тестовом файле")
