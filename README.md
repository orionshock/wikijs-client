# wikijs-client

A small Python CLI and library for practical Wiki.js GraphQL page operations.

## What it does

- exact page existence checks by path
- global text search
- predictable page listing
- page reads by exact path
- idempotent page upsert
- page move/rename
- optional delete
- script-friendly JSON output

## Top-level flags

- `--versioncheck`
  - checks the server version against the project target: `2.5.312`
  - warns when the server version differs

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
  - with no flags, shows the full `pages.list()` inventory
  - with `--query`, passes text into Wiki.js search
  - with `--path`, scopes Wiki.js search by path
  - `--regex` is an optional local post-filter over returned rows

`move` and `delete` support `--dry-run`.

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

## Metadata behavior

`upsert` preserves existing description and tags on update unless you explicitly replace them:

- `--replace-description`
- `--replace-tags`

## Configuration

Environment variables:

- `WIKIJS_URL`
- `WIKIJS_TOKEN`
- `WIKIJS_LOCALE` (optional, default: `en`)

## Python API

Top-level exports:

```python
from wikijs_client import (
    WikiJsClient,
    WikiJsError,
    WikiJsSchemaError,
    WikiJsConflictError,
    WikiJsValidationError,
    PageSummary,
    SiteVersion,
    PageDetail,
    PageTag,
    MutationResult,
)
```

Supported public client methods:

- `get_version(target_version: str = "") -> SiteVersion`
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
- `SiteVersion`: `currentVersion`, `latestVersion`, `latestVersionReleaseDate`, `upgradeCapable`, optional target comparison fields
- `MutationResult`: `action`, `succeeded`, `message`, `error_code`, optional `page`, `previousPage`, `changed`, `metadata`

Error types:

- `WikiJsError`: request or general operational failure
- `WikiJsSchemaError`: the deployment responded, but did not expose the schema shape this client expected
- `WikiJsConflictError`: a mutation failed due to a duplicate path or similar collision
- `WikiJsValidationError`: a mutation failed validation and should be fixed before retrying

## Notes

- exact path lookup uses targeted `pages.search(...)` plus exact client-side filtering
- `--versioncheck` queries `system.info` only when asked; there is no per-call version check tax
- `list` uses `pages.list()` with no filters, and `pages.search(...)` when `--query` or `--path` is used
- compatibility has been validated against one real Wiki.js environment so far

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```
