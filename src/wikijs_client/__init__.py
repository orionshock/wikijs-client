"""Public Python API for wikijs-client.

Supported top-level imports are intentionally small and stable:
- WikiJsClient
- WikiJsError
- WikiJsSchemaError
- WikiJsConflictError
- WikiJsValidationError
- PageSummary
- PageDetail
- PageTag
- SiteVersion
- MutationResult
"""

__all__ = ["WikiJsClient", "WikiJsError", "WikiJsSchemaError", "WikiJsConflictError", "WikiJsValidationError", "MutationResult", "PageDetail", "PageSummary", "PageTag", "SiteVersion"]

from .client import WikiJsClient, WikiJsError, WikiJsSchemaError, WikiJsConflictError, WikiJsValidationError
from .models import MutationResult, PageDetail, PageSummary, PageTag, SiteVersion
