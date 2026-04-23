# wikijs-client

A small Python CLI and library for practical Wiki.js GraphQL page operations.

The immediate form is a CLI, but the code should be shaped so it can also support:

- a reusable Python package
- a packaged Python executable
- an MCP server or other agent-facing wrapper

## Goals

- simple page reads by path
- idempotent page upsert
- basic listing/search
- optional delete
- minimal configuration
- script-friendly output
- clean separation between transport, domain logic, and interface layer

## Status

Early prototype, already validated against a live Wiki.js instance for read and basic page lifecycle operations.

## Current commands

- `exists`
- `search`
- `get`
- `list`
- `upsert`
- `move`
- `delete`

## Command semantics

The CLI now has an intentional split between three read/discovery modes:

- `exists PATH`
  - exact path presence check
  - best for scripts, agents, preflight checks, and conditional flows
  - exits non-zero when the page is missing

- `search TEXT`
  - global text search backed by Wiki.js `pages.search(path="", query=TEXT)`
  - best for discovery when you know a word, phrase, host, service, or concept but not the exact page path
  - returns ranked search results from the server rather than a full wiki listing

- `list`
  - predictable browse command backed by `pages.list()`
  - best for subtree browsing, broad inventories, and client-side filtering
  - supports `--prefix`, `--query`, and `--regex`

This split is deliberate:
- exact existence checks should not require listing the entire wiki
- global text search should use the server's search behavior when available
- subtree browsing should stay predictable even if Wiki.js search behavior changes

`move` and `delete` support `--dry-run` for agent/script planning without mutating the wiki.

Input normalization is intentionally lightweight:
- paths, titles, and tags are trimmed and validated more strictly because they are likely to become URLs, identifiers, or stable keys
- descriptions are validated more gently because they are human-facing text
- tags are sanitized for structural safety only, not semantic correctness

## Usage examples

```bash
export WIKIJS_URL='https://example.com/graphql'
export WIKIJS_TOKEN='your-token'

wikijs-client exists docs/getting-started
wikijs-client exists infrastructure/reverse-proxy/caddy --json
wikijs-client search reverse-proxy
wikijs-client search auth --json
wikijs-client list
wikijs-client list --prefix docs
wikijs-client list --prefix infrastructure/reverse-proxy
wikijs-client list --query onboarding
wikijs-client list --regex '^docs/'
wikijs-client get docs/getting-started
wikijs-client upsert docs/scratch 'Scratch Page' --file scratch.md
wikijs-client upsert docs/scratch 'Scratch Page' --file scratch.md --description 'replace me' --replace-description --tags notes scratch --replace-tags
wikijs-client move docs/scratch docs/reference --title 'Reference Page'
wikijs-client move docs/scratch docs/reference --dry-run
wikijs-client delete docs/scratch --dry-run
wikijs-client delete docs/scratch
```

Human-readable output is the default for mutation commands. Use `--json` when you want script-friendly structured output.

`exists` now performs exact path presence checks and exits non-zero when a page is missing.

`search` performs global text search through `pages.search(path="", query=TEXT)` and renders the returned results as a compact table by default.

`list` now renders a compact table by default, and can filter by:

- `--prefix`
- `--query` for case-insensitive substring matching
- `--regex` for regular expression matching

## Metadata update semantics

`upsert` tries to avoid surprising metadata loss.

- if a page already exists and you omit `--description`, the existing description is preserved
- if a page already exists and you omit `--tags`, the existing tags are preserved
- if you want to explicitly replace them, use:
  - `--replace-description`
  - `--replace-tags`

On create, omitted description/tags default to empty values.

## Configuration

Environment variables:

- `WIKIJS_URL`
- `WIKIJS_TOKEN`
- `WIKIJS_LOCALE` (optional, defaults to `en`)

## Public Python API

The Python-side architecture is intentionally split three ways:

- `client.py`
  - transport and normalized Wiki.js operations
  - public exports from that module should effectively be just `WikiJsClient` and `WikiJsError`
  - returns structured Python model objects rather than printing or formatting output

- `models.py`
  - small stable data contracts for normalized results
  - owns `PageSummary`, `PageDetail`, `PageTag`, and `MutationResult`

- `cli.py`
  - all command-line parsing, human output, JSON stdout rendering, and exit-code behavior
  - should not contain raw GraphQL or normalization logic that belongs in the client

The package top level re-exports the supported library surface for convenience:

```python
from wikijs_client import (
    WikiJsClient,
    WikiJsError,
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

Return-model expectations:

- `PageSummary`
  - stable compact page metadata for list/search results
  - fields: `id`, `path`, `title`, `description`

- `PageDetail`
  - detailed page payload for direct reads
  - fields: `id`, `path`, `title`, `content`, `description`, `tags`

- `PageTag`
  - normalized page tag
  - fields: `tag`, `title`

- `MutationResult`
  - normalized mutation result payload
  - fields: `action`, `succeeded`, `message`, `error_code`, optional `page`, optional `previous_page`, optional `changed`, optional `metadata`
  - `.to_dict()` keeps the response shape stable for scripts and tools

Stability notes:

- top-level imports listed above are intended to be the supported public package surface
- inside `client.py`, callers should treat `WikiJsClient` and `WikiJsError` as the only intended public module-level exports
- `WikiJsClient` public methods without a leading underscore are the intended reusable client API
- helper functions and methods prefixed with `_` are internal and may change without notice
- CLI behavior may evolve separately from the Python API as long as the core client contract stays clean

Example:

```python
from wikijs_client import WikiJsClient

client = WikiJsClient(url="https://example.com/graphql", token="secret-token")

if client.get_page_by_path("docs/getting-started") is None:
    result = client.create_page(
        path="docs/getting-started",
        title="Getting Started",
        content="# Getting Started\n",
    )
    print(result.to_dict())

for page in client.search_pages(query="reverse proxy"):
    print(page.path, page.title)
```

## Development direction

This project should stay **agnostic** to any one personal wiki layout or home-lab setup.

### Shape constraints

- keep the core client generic and reusable
- keep CLI concerns out of the API client
- avoid baking in personal paths, tags, titles, or assumptions about one wiki
- prefer explicit inputs over magical local conventions
- return structured results where possible
- keep it automation-friendly first, interactive second
- prefer agent/tool usability over decorative human CLI output
- do not add human-facing niceties that make machine consumption less predictable

### Intended architecture

- `client.py`: low-level Wiki.js GraphQL operations with normalized responses
- `models.py`: small stable dataclasses for page summaries, page detail, tags, and mutation results
- higher-level operations may later live in a service layer if the client grows
- `cli.py`: argument parsing and terminal UX only
- future adapters may expose the same core through MCP or another agent interface

### Roadmap

#### Completed foundation

Already in place:

- core CLI commands for `exists`, `search`, `get`, `list`, `upsert`, `move`, and `delete`
- normalized result models (`PageSummary`, `PageDetail`, `PageTag`, `MutationResult`)
- explicit separation between client transport, model objects, and CLI presentation
- stable top-level Python API exports with basic tests locking the public surface
- exact path lookup using targeted `pages.search(...)` plus exact client-side filtering, with `pages.list()` fallback when search misses an exact path
- basic mutation safety around metadata preservation and dry-run support for move/delete
- README coverage for command semantics, Python API shape, and compatibility assumptions
- test coverage for core client behavior, CLI flows, and exported public API

#### Next milestone, retrieval ergonomics and compatibility hardening

Goal: improve discovery and compatibility without blurring command semantics.

Likely work:

- add pagination controls for large wikis
- add explicit sorting controls where the API supports them cleanly
- evaluate whether exact-match or title/path helper queries can improve compatibility across more Wiki.js deployments
- evaluate whether the current list-based fallback for exact path lookup should remain enabled by default across more Wiki.js deployments
- validate locale configuration behavior across more Wiki.js deployments now that search locale can be supplied via `WIKIJS_LOCALE`

#### Next milestone, richer mutation contracts

Goal: make writes easier for scripts and agents to reason about.

Likely work:

- consider validate-style or preview flows where feasible
- improve conflict and schema-surprise reporting for missing pages, duplicate paths, or incompatible deployments
- add more tests around metadata preservation and replacement edge cases
- decide whether mutation result change summaries should grow into a more formal diff contract

#### Next milestone, packaging and release discipline

Goal: keep the core implementation ready for broader reuse.

Likely work:

- harden the package layout for publishing to PyPI if desired
- consider a single-file packaged executable for simple ops workflows
- add lightweight versioning and release discipline once the API shape settles
- keep the core library interface stable enough to back an MCP wrapper later

#### Next milestone, agent-facing adapters

Goal: support AI agent usage directly without compromising the clean core.

Likely work:

- design an MCP or similar adapter around the existing library instead of embedding agent logic into the CLI
- expose stable structured responses with minimal transformation
- keep auth/config simple and explicit for headless environments
- decide which operations are safe enough to expose by default in agent runtimes
- add integration examples once the core contract feels stable

### Possible future forms

1. **pip package**
   - reusable by agents, scripts, and other Python systems
2. **single packaged executable**
   - convenient for ops/admin workflows
3. **MCP wrapper**
   - useful when the same operations should be safely exposed to agent runtimes

The code should be written so those are packaging/interface decisions, not rewrites.

## Compatibility notes

Current validation target:

- a live Wiki.js GraphQL endpoint used during development
- page lifecycle tested live for create, update, read, and delete

Current assumptions:

- standard Wiki.js GraphQL `pages.list`, `pages.search`, `pages.single`, `pages.create`, `pages.update`, and `pages.delete`
- `pages.single` exposes `description` and `tags { tag title }`
- token-based API auth via `Authorization: Bearer ...`
- markdown editor mode

Failure modes handled explicitly now include:

- HTTP/request failures
- non-JSON API responses
- GraphQL error payloads
- missing `data` payloads
- ambiguous exact path matches during targeted search or list fallback lookup
- missing required env vars
- file read errors during CLI content loading

## Known limitations

- list output is currently unpaginated
- list filtering happens client-side after fetching the page list
- global text search depends on the current behavior and ranking of `pages.search(...)`
- exact path lookup now prefers `pages.search(...)` plus exact client-side path filtering, then falls back to `pages.list()` plus exact client-side filtering when search misses
- compatibility has been validated against one real Wiki.js environment so far, not a broad matrix of versions
- mutation results are normalized, but the client still relies on a limited subset of the Wiki.js GraphQL schema

This tool should remain conservative about relying on exotic or version-fragile fields.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```
