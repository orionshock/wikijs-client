# Python API

This page documents the supported Python API for `wikijs-client`.

## Top-level exports

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

## Supported public client methods

- `get_version(target_version: str = "") -> SiteVersion`
- `list_pages() -> list[PageSummary]`
- `search_pages(query: str, path: str = "") -> list[PageSummary]`
- `get_page_by_path(path: str) -> PageDetail | None`
- `create_page(...) -> MutationResult`
- `update_page(...) -> MutationResult`
- `upsert_page(...) -> MutationResult`
- `move_page(...) -> MutationResult`
- `delete_page_by_path(path: str) -> MutationResult`

## Core return models

- `PageSummary`: `id`, `path`, `title`, `description`
- `PageDetail`: `id`, `path`, `title`, `content`, `description`, `tags`
- `PageTag`: `tag`, `title`
- `SiteVersion`: `currentVersion`, `latestVersion`, `latestVersionReleaseDate`, `upgradeCapable`, optional target comparison fields
- `MutationResult`: `action`, `succeeded`, `message`, `error_code`, optional `page`, `previousPage`, `changed`, `metadata`

## Error types

- `WikiJsError`: request or general operational failure
- `WikiJsSchemaError`: the deployment responded, but did not expose the schema shape this client expected
- `WikiJsConflictError`: a mutation failed due to a duplicate path or similar collision
- `WikiJsValidationError`: a mutation failed validation and should be fixed before retrying
