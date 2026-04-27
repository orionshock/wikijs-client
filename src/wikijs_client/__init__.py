"""Public Python API for wikijs-client.

Supported top-level imports are intentionally small and stable:
- WikiJsClient
- WikiJsError
- WikiJsSchemaError
- WikiJsConflictError
- WikiJsAmbiguousMatchError
- WikiJsNotFoundError
- WikiJsValidationError
- PageSummary
- PageDetail
- PageTag
- SiteVersion
- MutationResult
- __version__
"""

from .client import (
    WikiJsAmbiguousMatchError,
    WikiJsClient,
    WikiJsConflictError,
    WikiJsError,
    WikiJsNotFoundError,
    WikiJsSchemaError,
    WikiJsValidationError,
)
from .models import MutationResult, PageDetail, PageSummary, PageTag, SiteVersion

__version__ = "0.1.2"

__all__ = [
    "WikiJsClient",
    "WikiJsError",
    "WikiJsSchemaError",
    "WikiJsConflictError",
    "WikiJsAmbiguousMatchError",
    "WikiJsNotFoundError",
    "WikiJsValidationError",
    "MutationResult",
    "PageDetail",
    "PageSummary",
    "PageTag",
    "SiteVersion",
    "__version__",
]
