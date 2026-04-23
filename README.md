# wikijs-client

A small Python CLI and library for practical Wiki.js GraphQL page operations.

## What it does

- exact page existence checks by path
- global text search
- predictable page listing with client-side filtering and pagination
- page reads by exact path
- idempotent page upsert
- page move/rename
- optional delete
- script-friendly JSON output

## Commands

- `exists`
- `search`
- `get`
- `list`
- `upsert`
- `move`
- `delete`

## Command semantics

- `exists PATH`
  - exact path presence check
  - exits non-zero when the page is missing

- `search TEXT`
  - global text search via Wiki.js `pages.search(path="", query=TEXT)`
  - best when you know a word or phrase but not the page path

- `list`
  - browse command backed by `pages.list()`
  - supports client-side filtering and pagination with `--prefix`, `--query`, `--regex`, `--limit`, and `--offset`

`move` and `delete` support `--dry-run`.

## Usage examples

```bash
export WIKIJS_URL='https://example.com/graphql'
export WIKIJS_TOKEN='your-token'

wikijs-client exists docs/getting-started
wikijs-client search reverse-proxy
wikijs-client list --prefix docs --limit 25 --offset 0
wikijs-client get docs/getting-started
wikijs-client upsert docs/scratch 'Scratch Page' --file scratch.md
wikijs-client move docs/scratch docs/reference --title 'Reference Page'
wikijs-client delete docs/scratch --dry-run
```

## Metadata behavior

`upsert` preserves existing description and tags on update unless you explicitly replace them:

- `--replace-description`
- `--replace-tags`

## Configuration

Environment variables:

- `WIKIJS_URL`
- `WIKIJS_TOKEN`
- `WIKIJS_LOCALE` (optional, default: `en`)
- `WIKIJS_EXACT_PATH_LOOKUP` (optional, `search` or `list`, default: `search`)

## Python API

Top-level exports:

```python
from wikijs_client import (
    WikiJsClient,
    WikiJsError,
    WikiJsSchemaError,
    PageSummary,
    PageDetail,
    PageTag,
    MutationResult,
)
```

Supported public client methods:

- `list_pages() -> list[PageSummary]`
- `search_pages(query: str, path: str = "") -> list[PageSummary]`
- `get_page_by_path(path: str) -> PageDetail | None`
- `create_page(...) -> MutationResult`
- `update_page(...) -> MutationResult`
- `upsert_page(...) -> MutationResult`
- `move_page(...) -> MutationResult`
- `delete_page_by_path(path: str) -> MutationResult`

Core return models:

- `PageSummary`: `id`, `path`, `title`, `description`
- `PageDetail`: `id`, `path`, `title`, `content`, `description`, `tags`
- `PageTag`: `tag`, `title`
- `MutationResult`: `action`, `succeeded`, `message`, `error_code`, optional `page`, `previousPage`, `changed`, `metadata`

Error types:

- `WikiJsError`: request, validation, or operational failure
- `WikiJsSchemaError`: the deployment responded, but did not expose the schema shape this client expected

## Notes

- exact path lookup is explicit: use `search` mode by default, or opt into `list` mode with `WIKIJS_EXACT_PATH_LOOKUP=list`
- list filtering and pagination are currently client-side
- compatibility has been validated against one real Wiki.js environment so far

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```
