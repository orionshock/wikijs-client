# Notes

## Current useful follow-ups

- Decide whether search locale should remain hardcoded to `en` or become configurable.
- Consider whether a list-based fallback for exact path lookup is worth keeping for compatibility with other Wiki.js deployments.
- If the Python API grows further, consider a small dedicated API reference doc in addition to the README section.

## Resolved / no longer primary concerns

- Exact path lookup no longer depends on fetching the full `pages.list()` result first.
- The CLI is now intentionally split between:
  - `exists` for exact path presence checks
  - `search` for global text discovery
  - `list` for predictable browse/subtree workflows
- The library boundary is now clearer:
  - `client.py` handles transport and normalized operations
  - `models.py` holds structured result objects
  - `cli.py` owns output formatting, JSON rendering, and terminal behavior
