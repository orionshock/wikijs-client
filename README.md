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
  - emit structured JSON instead of human-readable output
- `--quiet`
  - suppress successful stdout output; errors still go to stderr
- `--debug`
  - emit debug details to stderr without contaminating stdout

## Output modes

### Default mode

- human-readable stdout
- errors go to stderr

### `--json`

- emits structured JSON to stdout
- preserves typed exit codes
- can be used with normal commands and `--versioncheck`
- cannot be combined with `--quiet`

### `--quiet`

Actual contract:

- suppresses successful stdout output for all commands, including reads and mutations
- does not change exit codes
- does not suppress stderr
- still performs the underlying operation
- can be used either before or after the subcommand
- cannot be combined with `--json`

Practical examples:

- `exists --quiet`
  - prints nothing
  - exits `0` when found, `2` when missing
- `get --quiet`
  - prints nothing on success
  - still exits nonzero and prints an error on failure
- mutating commands with `--quiet`
  - still mutate on success
  - print nothing on success
  - still print errors to stderr

### `--debug`

- writes diagnostics to stderr only
- keeps stdout clean for human output or JSON pipelines
- never intentionally prints the auth token or other raw secrets

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
- `--dry-run`
  - preview whether upsert would create or update without mutating
- `--diff`
  - with `--dry-run`, include a unified diff of content changes
- `--quiet`
  - suppress successful stdout output
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
- `--quiet`
  - suppress successful stdout output
- `--json`
  - emit structured JSON

### `delete`

Delete a page by exact path.

Arguments and flags:
- `path`
  - exact page path to delete
- `--dry-run`
  - preview the delete without applying it
- `--quiet`
  - suppress successful stdout output
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

## Exit codes

The CLI uses typed exit codes so automation can distinguish common failure modes without parsing human-readable error text.

- `0` — success
- `1` — general failure
- `2` — not found
  - exact-path target does not exist
- `3` — ambiguous match
  - the client found more than one exact-path candidate and refused to guess
- `4` — validation, auth, config, schema, conflict, or file error
  - missing `WIKIJS_URL` / `WIKIJS_TOKEN`
  - invalid input
  - Wiki.js schema mismatch
  - mutation conflict or validation failure
  - local file read/write issue

Examples:

```bash
wikijs-client exists docs/missing
# exits 2 when missing

wikijs-client get docs/missing
# exits 2 when missing
```

## Installation

### Install with pip

Requires Python 3.12 or 3.13.

```bash
pip install wikijs-client
```

### Development install

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## Python API

The supported Python API docs live in `docs/python-api.md` and can be moved into the GitHub wiki if you want to keep the README CLI-focused.

Version metadata is also available at runtime:

```python
import wikijs_client
print(wikijs_client.__version__)
```

## Development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python -m build
python -m twine check dist/*
```
