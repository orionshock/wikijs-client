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
wikijs-tool delete ideas/scratch
```

Human-readable output is the default for mutation commands. Use `--json` when you want script-friendly structured output.

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

- tighten metadata semantics around descriptions/tags so updates are explicit and unsurprising
- improve output shaping for human vs automation use
- add more failure-path and compatibility tests
- document compatibility assumptions with Wiki.js versions
- consider lightweight structured models if raw dicts start getting mushy

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
- token-based API auth via `Authorization: Bearer ...`
- markdown editor mode

This tool should remain conservative about relying on exotic or version-fragile fields.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```
