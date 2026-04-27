# wikijs-client

A small Python CLI and library for practical Wiki.js GraphQL page operations.

## What it does

- exact path checks
- global text search
- predictable page listing
- page reads by exact path
- idempotent page upsert
- page move/rename
- page delete with explicit confirmation
- script-friendly JSON output

## Commands

### Global options

- `--versioncheck`
  - check the server version against the project target (`2.5.312`)
- `--json`
  - emit structured JSON instead of human-readable output
- `--quiet`
  - suppress successful stdout output; errors still go to stderr
- `--debug`
  - emit debug details to stderr without contaminating stdout

### `list`

List pages for browsing or server-backed discovery.

Flags:
- `--query QUERY`
- `--path PATH`
- `--regex REGEX`
- `--json`

### `search`

Search pages globally by text.

Arguments and flags:
- `text`
- `--json`

### `exists`

Check whether a page exists at an exact path.

Arguments and flags:
- `path`
- `--json`

### `get`

Fetch page content by exact path.

Arguments and flags:
- `path`
- `--json`

### `upsert`

Create a page when it does not exist, or update it when it does.

Arguments:
- `path`
- `title`

Flags:
- `--file FILE`
- `--description DESCRIPTION`
- `--tags [TAGS ...]`
- `--replace-description`
- `--replace-tags`
- `--dry-run`
- `--diff`
- `--quiet`
- `--json`

### `move`

Move a page to a new path, optionally changing the title.

Arguments:
- `source_path`
- `destination_path`

Flags:
- `--title TITLE`
- `--dry-run`
- `--quiet`
- `--json`

### `delete`

Delete a page by exact path.

For safety, real deletes require `--force`.

Arguments and flags:
- `path`
- `--dry-run`
- `--force`
- `--quiet`
- `--json`

## Usage examples

```bash
wikijs-client exists docs/getting-started
wikijs-client delete docs/scratch --dry-run
```

## Installation

Requires Python 3.11, 3.12, or 3.13.

### Install with pip

```bash
pip install wikijs-client
```

### Development install

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## More documentation

For deeper behavior and contract details, use the project wiki:

- Wiki: <https://github.com/orionshock/wikijs-client/wiki>

That is the right place for:
- library behavior details
- mutation JSON shape and examples
- dry-run semantics
- exact-path safety details
- automation guidance
- longer walkthroughs

## Development

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python -m build
python -m twine check dist/*
```
