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

- `--versioncheck` check the server version against the project target (`2.5.312`)
- `--json` emit structured JSON instead of human-readable output
- `--quiet` suppress successful stdout output; errors still go to stderr
- `--debug` emit debug details to stderr without contaminating stdout

### `list`
List pages for browsing or server-backed discovery.
- `--query QUERY`
- `--path PATH`
- `--regex REGEX`

### `search`
Search pages globally by text.
- `text`
- `--json`

### `exists`
Check whether a page exists at an exact path.
- `path`

### `get`
Fetch page content by exact path.
- `path`
- `--file FILE`

### `upsert`
Create a page when it does not exist, or update it when it does.
- `path` -- Required
- `title` -- Required
- `--file FILE`
- `--description DESCRIPTION`
- `--tags [TAGS ...]`
- `--replace-description`
- `--replace-tags`
- `--dry-run`
- `--diff`

### `move`
Move a page to a new path, optionally changing the title.
- `source_path` -- Required
- `destination_path` --Required
- `--title TITLE`
- `--dry-run`

### `delete`
Delete a page by exact path.
For safety, real deletes require `--force`.
- `path`
- `--dry-run`

## Usage examples

```bash
wikijs-client exists docs/getting-started
wikijs-client get docs/getting-started --file getting-started.md
wikijs-client delete docs/scratch --dry-run
```

## Installation

Requires Python 3.11, 3.12, or 3.13.

```bash
pip install wikijs-client
```

## More documentation

For deeper behavior and contract details, use the project wiki:
<https://github.com/orionshock/wikijs-client/wiki>
