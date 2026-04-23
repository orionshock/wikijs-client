# Milestones

This file is the project scratchpad for future work.

## Near-term ideas

- probe whether any Wiki.js deployments expose a more direct exact-match helper than the current `pages.search(...)` + exact client-side filtering
- improve create/update/delete conflict reporting when the API returns richer duplicate-path or validation errors
- add more tests around metadata preservation and replacement edge cases
- decide whether `MutationResult.changed` should grow into a more formal diff contract

## Possible feature work

- explicit sorting controls for `list` where the API supports them cleanly
- validate-style or preview flows for mutations where feasible
- server-side pagination if it is practical and portable across Wiki.js deployments
- lightweight versioning and release discipline once the API shape settles

## Packaging / interface directions

- harden the package layout for publishing to PyPI if desired
- consider a single-file packaged executable for simple ops workflows
- add an MCP or similar adapter around the existing library instead of embedding agent logic into the CLI
- document which operations are safe to expose by default in agent runtimes

## General design reminders

- keep the core client generic and reusable
- keep CLI concerns out of the API client
- prefer explicit inputs over magical local conventions
- keep machine consumption predictable
- preserve a small, stable public Python API
