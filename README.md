# Визуализация графа зависимостей Ubuntu APT — вариант 16

## Описание

CLI-инструмент для анализа графа зависимостей пакетов Ubuntu APT.
Сейчас реализован **этап 1**: приём, проверка и вывод конфигурации.
Получение зависимостей и генерация SVG будут добавлены на следующих этапах.

## Требования

Python 3.9+; внешние Python-библиотеки для этапа 1 не требуются.

## Опции

| Опция | Значение |
|---|---|
| `--package` | Имя пакета, например `bash` |
| `--source` | URL репозитория или путь к тестовому файлу |
| `--test-mode` | Переключатель тестового режима (по умолчанию выключен) |
| `--version` | Версия анализируемого пакета |
| `--output` | Имя SVG-файла, который будет создан на этапе 5 |

Все опции, кроме переключателя `--test-mode`, обязательны. При ошибках
программа печатает объяснение и завершает работу с ненулевым кодом.

## Запуск

В командной строке Windows из папки проекта:

```bat
run.bat --package bash --source https://archive.ubuntu.com/ubuntu --version 5.2.21-2ubuntu4 --output graph.svg
```

Linux/macOS:

```sh
sh run.sh --package bash --source https://archive.ubuntu.com/ubuntu --version 5.2.21-2ubuntu4 --output graph.svg
```

Тестовый режим (имя пакета на данном этапе проверяется по правилам
Ubuntu; формат графа будет реализован на этапе 3):

```bat
run.bat --package a --source tests/example_repo.txt --test-mode --version 1.0 --output graph.svg
```

## Запуск тестов

```bat
python -m unittest discover -s tests -v
```

## Пример вывода

```text
package: bash
source: https://archive.ubuntu.com/ubuntu
test_mode: False
version: 5.2.21-2ubuntu4
output: graph.svg
```

## Ограничения текущего этапа

URL проверяется по форме, но соединение с сетью не выполняется. Версия
проверяется синтаксически; наличие версии в репозитории не проверяется.
Изображение на этом этапе не создаётся.

## План коммитов

1. `feat(cli): add configuration parsing and validation` — этап 1.
2. `feat(apt): load direct package dependencies` — этап 2.
3. `feat(graph): build dependency graph using BFS` — этап 3.
4. `feat(order): calculate dependency loading order` — этап 4.
5. `feat(graphviz): export dependency graph to SVG` — этап 5.
