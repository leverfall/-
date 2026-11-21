"""Unit tests for direct Ubuntu APT package dependency extraction."""

import gzip
import io
import lzma
import unittest
from unittest.mock import patch

from src.apt_repository import (
    RepositoryError, fetch_index, get_direct_dependencies, index_url,
    parse_stanzas, split_dependencies,
)


PACKAGES = """Package: bash
Version: 5.2.21-2ubuntu4
Architecture: amd64
Pre-Depends: libc6 (>= 2.38)
Depends: base-files (>= 12), libtinfo6 (>= 6.4) | libtinfo5,
 foo:any (>= 1.0)

Package: bash
Version: 1.0
Depends: other

Package: empty
Version: 1.0

"""


class AptRepositoryTests(unittest.TestCase):
    """Verify decoding, matching exact versions, and dependency fields."""

    def test_url_base(self):
        self.assertEqual(
            index_url("https://archive.ubuntu.com/ubuntu"),
            "https://archive.ubuntu.com/ubuntu/"
            "dists/noble/main/binary-amd64/Packages.xz",
        )

    def test_url_explicit(self):
        url = (
            "https://example.org/dists/jammy/universe/"
            "binary-amd64/Packages.gz"
        )
        self.assertEqual(index_url(url), url)

    def test_records(self):
        self.assertEqual(len(list(parse_stanzas(PACKAGES))), 3)

    def test_dependencies(self):
        self.assertEqual(
            split_dependencies("a (>= 1, 2), b | c, d"),
            ["a (>= 1, 2)", "b | c", "d"],
        )

    @patch("src.apt_repository.fetch_index", return_value=PACKAGES)
    def test_exact_version(self, _fetch):
        result = get_direct_dependencies("https://example.org", "bash", "1.0")
        self.assertEqual(result, ["other"])

    @patch("src.apt_repository.fetch_index", return_value=PACKAGES)
    def test_predepends_and_wrapped_field(self, _fetch):
        result = get_direct_dependencies(
            "https://example.org", "bash", "5.2.21-2ubuntu4"
        )
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], "libc6 (>= 2.38)")
        self.assertIn("foo:any (>= 1.0)", result)
        self.assertIn("libtinfo6 (>= 6.4) | libtinfo5", result)

    @patch("src.apt_repository.fetch_index", return_value=PACKAGES)
    def test_missing_version(self, _fetch):
        with self.assertRaises(RepositoryError):
            get_direct_dependencies("https://example.org", "bash", "2.0")

    @patch("src.apt_repository.fetch_index", return_value=PACKAGES)
    def test_no_dependencies(self, _fetch):
        result = get_direct_dependencies("https://example.org", "empty", "1.0")
        self.assertEqual(result, [])

    def test_gzip_index(self):
        payload = gzip.compress(PACKAGES.encode())
        self.assertEqual(self.decode_payload(payload, "Packages.gz"), PACKAGES)

    def test_xz_index(self):
        payload = lzma.compress(PACKAGES.encode())
        self.assertEqual(self.decode_payload(payload, "Packages.xz"), PACKAGES)

    def decode_payload(self, payload, suffix):
        class Response(io.BytesIO):
            pass

        url = "https://example.org/dists/noble/main/binary-amd64/" + suffix
        with patch(
            "src.apt_repository.urlopen", return_value=Response(payload)
        ):
            return fetch_index(url)


if __name__ == "__main__":
    unittest.main()
