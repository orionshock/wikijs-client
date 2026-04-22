"""Public Python API for wikijs-client.

Supported top-level imports are intentionally small and stable:
- WikiJsClient
- WikiJsError
- PageSummary
- PageDetail
- PageTag
- MutationResult
"""

__all__ = ["WikiJsClient", "WikiJsError", "MutationResult", "PageDetail", "PageSummary", "PageTag"]

from .client import WikiJsClient, WikiJsError
from .models import MutationResult, PageDetail, PageSummary, PageTag
