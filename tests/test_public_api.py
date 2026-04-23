from wikijs_client import MutationResult, PageDetail, PageSummary, PageTag, WikiJsClient, WikiJsError, WikiJsSchemaError


def test_top_level_exports_are_available():
    assert WikiJsClient is not None
    assert WikiJsError is not None
    assert WikiJsSchemaError is not None
    assert PageSummary is not None
    assert PageDetail is not None
    assert PageTag is not None
    assert MutationResult is not None


def test_top_level_all_includes_supported_public_api():
    import wikijs_client

    assert wikijs_client.__all__ == [
        "WikiJsClient",
        "WikiJsError",
        "WikiJsSchemaError",
        "MutationResult",
        "PageDetail",
        "PageSummary",
        "PageTag",
    ]
