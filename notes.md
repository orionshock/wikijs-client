# Notes

## Wiki.js path lookup observations

Current `get_page_by_path()` behavior in the tool is:
1. fetch full `pages.list`
2. scan client-side for a path match
3. fetch `pages.single(id: ...)`

That is workable for a small wiki, but it is the current main design smell because:
- every path lookup depends on listing the entire wiki first
- `get`, `upsert`, `move`, and `delete` all inherit that cost
- it gets less attractive as the wiki grows
- it is awkward for agent usage where repeated lookups are common

## GraphQL Playground findings

Observed query shape:

```graphql
query {
  pages {
    search(
      path: "infrastructure/newcaprica/docker-caddy"
      locale: "en"
      query: ""
    ) {
      results {
        id
        path
        title
      }
    }
  }
}
```

Observed result shape:

```json
{
  "data": {
    "pages": {
      "search": {
        "results": [
          {
            "id": "7",
            "path": "infrastructure/newcaprica/docker-caddy",
            "title": "Caddy"
          }
        ]
      }
    }
  }
}
```

Interpretation so far:
- `query: ""` seems to disable text search and leave path-focused narrowing in place
- in current live probing against Orion's wiki, `path` behaved more strictly than expected and returned results only for exact-looking paths, not loose prefixes or slash variants
- the client should still enforce exact match via `result.path == target_path` instead of trusting that behavior long-term
- exact-match filtering remains the safer contract even if the current server behavior is already effectively exact

## Reasonable next-step design

Potential replacement strategy for `get_page_by_path()`:
1. call `pages.search(path=<target>, locale="en", query="")`
2. exact-match filter returned results by `result.path == target`
3. if exactly one match, use it
4. if zero matches, treat as missing
5. if multiple exact matches somehow appear, fail clearly

This would likely be cheaper and cleaner than full `pages.list()` for normal lookups while still being conservative.

## TODO

- [x] Verify search result behavior for near-prefix collisions
- [x] Verify behavior for nonexistent paths
- [ ] Verify whether locale should remain hardcoded to `en` or become configurable
- [x] Implement a targeted path lookup helper using `pages.search(...)`
- [ ] Keep current `pages.list()` path-scan as fallback only if needed for compatibility
- [x] Add tests for exact-match filtering and ambiguous results
- [x] Document the lookup strategy clearly in code comments and README
