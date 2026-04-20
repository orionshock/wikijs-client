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

Early prototype, already validated against a live Wiki.js instance for read operations.

## Current commands

- `get`
- `list`
- `upsert`
- `delete`

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

- validate and harden `upsert`
- validate and harden `delete`
- improve error handling and GraphQL failure reporting
- support JSON output consistently
- support stdin/file-driven content updates cleanly
- add tests for core page lifecycle behavior
- document compatibility assumptions with Wiki.js versions

### Possible future forms

1. **pip package**
   - reusable by agents, scripts, and other Python systems
2. **single packaged executable**
   - convenient for ops/admin workflows
3. **MCP wrapper**
   - useful when the same operations should be safely exposed to agent runtimes

The code should be written so those are packaging/interface decisions, not rewrites.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```
