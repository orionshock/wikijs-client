# wikijs-graphql-tool

A small Python tool for practical Wiki.js GraphQL page operations.

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

- `get`
- `list`
- `upsert`
- `delete`

## Usage examples

```bash
export WIKIJS_URL='https://example.com/graphql'
export WIKIJS_TOKEN='your-token'

wikijs-tool list --prefix ideas
wikijs-tool get ideas/homeos
wikijs-tool upsert ideas/scratch 'Scratch Page' --file scratch.md
wikijs-tool upsert ideas/scratch 'Scratch Page' --file scratch.md --description 'replace me' --replace-description --tags notes scratch --replace-tags
wikijs-tool delete ideas/scratch
```

Human-readable output is the default for mutation commands. Use `--json` when you want script-friendly structured output.

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

### Intended architecture

- `client.py`: low-level Wiki.js GraphQL operations
- higher-level operations may later live in a service layer if the client grows
- `cli.py`: argument parsing and terminal UX only
- future adapters may expose the same core through MCP or another agent interface

### Near-term development points

- improve output shaping for human vs automation use
- add more failure-path and compatibility tests
- document compatibility assumptions with Wiki.js versions
- consider lightweight structured models if raw dicts start getting mushy
- consider page search/filter support beyond prefix matching

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

- standard Wiki.js GraphQL `pages.list`, `pages.single`, `pages.create`, `pages.update`, and `pages.delete`
- `pages.single` exposes `description` and `tags { tag title }`
- token-based API auth via `Authorization: Bearer ...`
- markdown editor mode

Failure modes handled explicitly now include:

- HTTP/request failures
- non-JSON API responses
- GraphQL error payloads
- missing `data` payloads
- missing required env vars
- file read errors during CLI content loading

This tool should remain conservative about relying on exotic or version-fragile fields.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```
