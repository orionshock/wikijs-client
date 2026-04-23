"""Public Python API for wikijs-client.

Supported top-level imports are intentionally small and stable:
- WikiJsClient
- WikiJsError
- WikiJsSchemaError
- PageSummary
- PageDetail
- PageTag
- MutationResult
"""

__all__ = ["WikiJsClient", "WikiJsError", "WikiJsSchemaError", "MutationResult", "PageDetail", "PageSummary", "PageTag"]

from .client import WikiJsClient, WikiJsError, WikiJsSchemaError
from .models import MutationResult, PageDetail, PageSummary, PageTag
