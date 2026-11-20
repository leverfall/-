"""CLI configuration and direct APT dependencies (stages 1–2)."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

from src.apt_repository import (
    RepositoryError, get_direct_dependencies, get_test_dependencies
)


PACKAGE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
TEST_PACKAGE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z]*$")
VERSION_PATTERN = re.compile(r"^[0-9][A-Za-z0-9.+:~\-]*$")


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
        description="Анализатор зависимостей Ubuntu APT (этап 2)"
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
    return parser


def main(argv=None):
    """Validate CLI input and display direct package dependencies."""
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
        if args.test_mode:
            dependencies = get_test_dependencies(args.source, args.package)
        else:
            dependencies = get_direct_dependencies(
                args.source, args.package, args.version
            )
    except RepositoryError as error:
        parser.exit(1, f"Ошибка: {error}\n")
    print("\nПрямые зависимости:")
    if not dependencies:
        print("  (отсутствуют)")
    for dependency in dependencies:
        print(f"  - {dependency}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
