# wikijs-graphql-tool

A small Python CLI for practical Wiki.js GraphQL page operations.

## Goals

- simple page reads by path
- idempotent page upsert
- basic listing/search
- optional delete
- minimal configuration
- script-friendly output

## Status

Early local prototype.

## Planned commands

- `get`
- `list`
- `upsert`
- `delete`

## Config

Environment variables:

- `WIKIJS_URL`
- `WIKIJS_TOKEN`

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```
