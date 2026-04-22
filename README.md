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

wikijs-client exists ideas/homeos
wikijs-client exists infrastructure/newcaprica/docker-caddy --json
wikijs-client search newcaprica
wikijs-client search openclaw --json
wikijs-client list
wikijs-client list --prefix ideas
wikijs-client list --prefix infrastructure/newcaprica
wikijs-client list --query homeos
wikijs-client list --regex '^ideas/'
wikijs-client get ideas/homeos
wikijs-client upsert ideas/scratch 'Scratch Page' --file scratch.md
wikijs-client upsert ideas/scratch 'Scratch Page' --file scratch.md --description 'replace me' --replace-description --tags notes scratch --replace-tags
wikijs-client move ideas/scratch ideas/reference --title 'Reference Page'
wikijs-client move ideas/scratch ideas/reference --dry-run
wikijs-client delete ideas/scratch --dry-run
wikijs-client delete ideas/scratch
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

#### Milestone 1, solid core CLI and library spine

Goal: make the current read/list/upsert/delete tool feel dependable as a small reusable core.

Desirable work:

- add more failure-path and compatibility tests
- tighten docstrings and internal API expectations around normalized models
- make sure CLI JSON output stays stable and predictable for agent/tool callers
- document compatibility assumptions with Wiki.js versions and schema expectations
- keep transport, model, and CLI responsibilities clearly separated

#### Milestone 2, stronger retrieval and query ergonomics

Goal: improve how agents and scripts discover pages without turning the tool into a fuzzy magic layer.

Desirable work:

- add pagination controls for large wikis
- add explicit sorting controls where the API supports them cleanly
- consider exact-match and title/path helper queries if they can remain predictable
- consider a search-oriented command that stays schema-conservative and machine-friendly
- make large result sets easier to consume without prioritizing decorative terminal output

#### Milestone 3, safer mutation workflows

Goal: make writes more trustworthy and easier for agents to reason about.

Desirable work:

- expand mutation result data so callers can reliably inspect what changed
- consider dry-run or validate-style flows where feasible
- consider clearer conflict/error reporting for missing pages, duplicate paths, or schema surprises
- add tests around metadata preservation and replacement edge cases
- document write semantics carefully so omission vs replacement stays explicit

#### Milestone 4, packaging for broader reuse

Goal: keep the core implementation ready for use beyond one local CLI.

Desirable work:

- harden the package layout for publishing to PyPI if desired
- consider a single-file packaged executable for simple ops workflows
- keep the core library interface stable enough to back an MCP wrapper later
- avoid interface decisions that would force a rewrite for agent-facing adapters
- add a small versioning/release discipline once the API shape settles

#### Milestone 5, agent-first interface layer

Goal: support AI agent usage directly without compromising the clean core.

Desirable work:

- design an MCP or similar adapter around the existing library instead of embedding agent logic into the CLI
- expose stable structured responses with minimal transformation
- keep auth/config simple and explicit for headless environments
- decide which operations are safe enough to expose by default in agent runtimes
- add example agent integration docs once the core contract feels stable

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

- Wiki.js GraphQL endpoint from Orion's local Wiki.js service
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
- ambiguous exact path matches during targeted search lookup
- missing required env vars
- file read errors during CLI content loading

## Known limitations

- list output is currently unpaginated
- list filtering happens client-side after fetching the page list
- global text search depends on the current behavior and ranking of `pages.search(...)`
- exact path lookup now prefers `pages.search(...)` plus exact client-side path filtering, so it still depends on current Wiki.js search behavior and schema stability
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
