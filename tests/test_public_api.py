from wikijs_client import MutationResult, PageDetail, PageSummary, PageTag, SiteVersion, WikiJsClient, WikiJsConflictError, WikiJsError, WikiJsSchemaError, WikiJsValidationError, __version__


def test_top_level_exports_are_available():
    assert WikiJsClient is not None
    assert WikiJsError is not None
    assert WikiJsSchemaError is not None
    assert WikiJsConflictError is not None
    assert WikiJsValidationError is not None
    assert PageSummary is not None
    assert PageDetail is not None
    assert SiteVersion is not None
    assert PageTag is not None
    assert MutationResult is not None
    assert __version__ == "0.1.1"


def test_top_level_all_includes_supported_public_api():
    import wikijs_client

    assert wikijs_client.__all__ == [
        "WikiJsClient",
        "WikiJsError",
        "WikiJsSchemaError",
        "WikiJsConflictError",
        "WikiJsValidationError",
        "MutationResult",
        "PageDetail",
        "PageSummary",
        "PageTag",
        "SiteVersion",
        "__version__",
    ]
