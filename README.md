# wikijs-client

A small Python CLI and library for practical Wiki.js GraphQL page operations.

## What it does

- exact path checks
- global text search
- predictable page listing
- page reads by exact path
- idempotent page upsert
- page move/rename
- optional delete
- script-friendly JSON output

## Commands

### Global options

- `--versioncheck`
  - check the server version against the project target (`2.5.312`)
- `--json`
  - emit structured JSON instead of human-readable output for `--versioncheck`

### `list`

List pages for browsing or server-backed discovery.

Use `--query` to pass text into Wiki.js search, `--path` to scope search by path, and `--regex` for optional local post-filtering.

Flags:
- `--query QUERY`
  - text to pass to Wiki.js search query
- `--path PATH`
  - path to pass to Wiki.js search for scoped discovery
- `--regex REGEX`
  - regular expression filter across returned path, title, and description
- `--json`
  - emit structured JSON instead of a table

### `search`

Search pages globally by text using Wiki.js search results.

This is the preferred global text search command when you want ranked search results rather than full-wiki list filtering.

Arguments and flags:
- `text`
  - search text to send to Wiki.js search
- `--json`
  - emit structured JSON instead of a table

### `exists`

Check whether a page exists at an exact path.

This is intended for machine-friendly existence checks.

Arguments and flags:
- `path`
  - exact page path to check
- `--json`
  - emit structured JSON instead of human-readable output

### `get`

Fetch page content by exact path.

Arguments and flags:
- `path`
  - exact page path to fetch
- `--json`
  - emit structured JSON instead of raw page content

### `upsert`

Create a page when it does not exist, or update it when it does.

Arguments:
- `path`
  - page path to create or update
- `title`
  - page title to create or set

Flags:
- `--file FILE`
  - read page content from a file instead of stdin
- `--description DESCRIPTION`
  - set page description
- `--tags [TAGS ...]`
  - set page tags
- `--replace-description`
  - replace existing description instead of preserving it when omitted
- `--replace-tags`
  - replace existing tags instead of preserving them when omitted
- `--json`
  - emit structured JSON

### `move`

Move a page to a new path, optionally changing the title.

Arguments:
- `source_path`
  - existing page path
- `destination_path`
  - new page path

Flags:
- `--title TITLE`
  - optional new title; defaults to the existing title
- `--dry-run`
  - preview the move without applying it
- `--json`
  - emit structured JSON

### `delete`

Delete a page by exact path.

Arguments and flags:
- `path`
  - exact page path to delete
- `--dry-run`
  - preview the delete without applying it
- `--json`
  - emit structured JSON

## Usage examples

```bash
export WIKIJS_URL='https://example.com/graphql'
export WIKIJS_TOKEN='your-token'

wikijs-client --versioncheck
wikijs-client --versioncheck --json
wikijs-client exists docs/getting-started
wikijs-client search reverse-proxy
wikijs-client list
wikijs-client list --query reverse-proxy
wikijs-client list --path infrastructure
wikijs-client get docs/getting-started
wikijs-client upsert docs/scratch 'Scratch Page' --file scratch.md
wikijs-client move docs/scratch docs/reference --title 'Reference Page'
wikijs-client delete docs/scratch --dry-run
```

## Configuration

Environment variables:

- `WIKIJS_URL`
- `WIKIJS_TOKEN`
- `WIKIJS_LOCALE` (optional, default: `en`)

## Installation

### Install with pip

```bash
pip install wikijs-client
```

### Development install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## Python API

The supported Python API docs live in `docs/python-api.md` and can be moved into the GitHub wiki if you want to keep the README CLI-focused.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python -m build
python -m twine check dist/*.tar.gz
python -m twine check --ignore-unrecognized dist/*.whl
```
