from __future__ import annotations

import pytest
import requests

from wikijs_client.client import WikiJsClient, WikiJsConflictError, WikiJsError, WikiJsSchemaError, WikiJsValidationError
from wikijs_client.models import MutationResult, PageDetail, PageTag


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}")

    def json(self):
        return self._payload


def test_get_page_by_path_returns_none_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(query, variables=None):
        return {"pages": {"search": {"results": []}}}

    monkeypatch.setattr(client, "_post", fake_post)
    assert client.get_page_by_path("bar") is None


def test_get_page_by_path_fetches_single_page(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    calls = []

    def fake_post(query, variables=None):
        calls.append((query, variables))
        if "search(path:" in query:
            return {"pages": {"search": {"results": [{"id": 7, "path": "ideas/homeos", "title": "HomeOS"}]}}}
        return {"pages": {"single": {"id": 7, "path": "ideas/homeos", "title": "HomeOS", "content": "body", "description": "desc", "tags": [{"tag": "ideas", "title": "ideas"}]}}}

    monkeypatch.setattr(client, "_post", fake_post)
    page = client.get_page_by_path("ideas/homeos")
    assert page is not None
    assert page.content == "body"
    assert isinstance(page, PageDetail)
    assert len(calls) == 2
    assert calls[0][1] == {"path": "ideas/homeos", "query": "", "locale": "en"}
    assert calls[1][1] == {"id": 7}


def test_get_page_by_path_normalizes_path_before_search(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    seen = {}

    def fake_search(path):
        seen["path"] = path
        return None

    monkeypatch.setattr(client, "_find_page_summary_by_path_via_search", fake_search)
    assert client.get_page_by_path(" /ideas/homeos/ ") is None
    assert seen["path"] == "ideas/homeos"


def test_search_pages_uses_search_query(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    captured = {}

    def fake_post(query, variables=None):
        captured["query"] = query
        captured["variables"] = variables
        return {"pages": {"search": {"results": [{"id": 7, "path": "ideas/homeos", "title": "HomeOS"}]}}}

    monkeypatch.setattr(client, "_post", fake_post)
    results = client.search_pages(query="homeos")
    assert len(results) == 1
    assert results[0].path == "ideas/homeos"
    assert "search(path:" in captured["query"]
    assert captured["variables"] == {"path": "", "query": "homeos", "locale": "en"}


def test_search_lookup_filters_non_exact_matches(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(query, variables=None):
        return {
            "pages": {
                "search": {
                    "results": [
                        {"id": 1, "path": "ideas/homeos-old", "title": "Old"},
                        {"id": 7, "path": "ideas/homeos", "title": "HomeOS"},
                    ]
                }
            }
        }

    monkeypatch.setattr(client, "_post", fake_post)
    match = client._find_page_summary_by_path_via_search("ideas/homeos")
    assert match is not None
    assert match.id == 7
    assert match.path == "ideas/homeos"


def test_search_lookup_raises_on_ambiguous_exact_matches(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(query, variables=None):
        return {
            "pages": {
                "search": {
                    "results": [
                        {"id": 7, "path": "ideas/homeos", "title": "HomeOS"},
                        {"id": 8, "path": "ideas/homeos", "title": "HomeOS Duplicate"},
                    ]
                }
            }
        }

    monkeypatch.setattr(client, "_post", fake_post)
    with pytest.raises(WikiJsError, match="Multiple pages matched path exactly via pages.search"):
        client._find_page_summary_by_path_via_search("ideas/homeos")


def test_list_pages_without_filters_uses_pages_list(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    captured = {}

    def fake_post(query, variables=None):
        captured["query"] = query
        captured["variables"] = variables
        return {"pages": {"list": [{"id": 7, "path": "ideas/homeos", "title": "HomeOS", "description": "desc"}]}}

    monkeypatch.setattr(client, "_post", fake_post)
    pages = client.list_pages()
    assert len(pages) == 1
    assert "list(orderBy: PATH)" in captured["query"]
    assert captured["variables"] is None


def test_upsert_page_creates_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)
    monkeypatch.setattr(
        client,
        "create_page",
        lambda **kwargs: MutationResult(
            action="created",
            succeeded=True,
            message="Page created successfully.",
            error_code=0,
            page={"id": 1, "path": kwargs["path"], "title": kwargs["title"]},
            changed={"created": True, "updated": False, "deleted": False},
        ),
    )

    result = client.upsert_page(path="ideas/test", title="Test", content="# Test")
    assert result.action == "created"
    assert result.succeeded is True
    assert result.changed["created"] is True
    assert result.changed["updated"] is False


def test_upsert_page_updates_when_existing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: PageDetail(id=99, path=path, title="Old", content="old", description="kept", tags=[PageTag(tag="ideas", title="ideas")]))
    captured = {}

    def fake_update_page(**kwargs):
        captured.update(kwargs)
        return MutationResult(action="updated", succeeded=True, message="Page has been updated.", error_code=0)

    monkeypatch.setattr(client, "update_page", fake_update_page)

    result = client.upsert_page(path="ideas/test", title="Test", content="# Test")
    assert result.action == "updated"
    assert result.succeeded is True
    assert captured["description"] == "kept"
    assert captured["tags"] == ["ideas"]
    assert result.metadata["description_preserved"] is True
    assert result.metadata["tags_preserved"] is True
    assert result.previous_page == {
        "id": 99,
        "path": "ideas/test",
        "title": "Old",
        "description": "kept",
        "tags": [{"tag": "ideas", "title": "ideas"}],
    }
    assert result.page == {
        "id": 99,
        "path": "ideas/test",
        "title": "Test",
        "description": "kept",
        "tags": [{"tag": "ideas", "title": ""}],
    }
    assert result.changed["updated"] is True
    assert result.changed["title"] is True
    assert result.changed["description"] is False
    assert result.changed["tags"] is False
    assert result.changed["content"] is True


def test_upsert_page_can_replace_description_and_tags(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: PageDetail(id=99, path=path, title="Old", content="old", description="kept", tags=[PageTag(tag="ideas", title="ideas")]))
    captured = {}

    def fake_update_page(**kwargs):
        captured.update(kwargs)
        return MutationResult(action="updated", succeeded=True, message="Page has been updated.", error_code=0)

    monkeypatch.setattr(client, "update_page", fake_update_page)

    result = client.upsert_page(
        path="ideas/test",
        title="Test",
        content="# Test",
        description="new desc",
        tags=["new", "tags"],
        preserve_description=False,
        preserve_tags=False,
    )
    assert captured["description"] == "new desc"
    assert captured["tags"] == ["new", "tags"]
    assert result.metadata["description_preserved"] is False
    assert result.metadata["tags_preserved"] is False
    assert result.changed["description"] is True
    assert result.changed["tags"] is True


def test_move_page_updates_path_and_preserves_existing_content(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(
        client,
        "get_page_by_path",
        lambda path: PageDetail(id=42, path="ideas/old", title="Old Title", content="body", description="desc", tags=[PageTag(tag="notes", title="notes")]) if path == "ideas/old" else None,
    )
    captured = {}

    def fake_update_page(**kwargs):
        captured.update(kwargs)
        return MutationResult(action="updated", succeeded=True, message="Page has been updated.", error_code=0)

    monkeypatch.setattr(client, "update_page", fake_update_page)
    result = client.move_page(source_path="ideas/old", destination_path="ideas/new")
    assert result.action == "moved"
    assert captured["page_id"] == 42
    assert captured["path"] == "ideas/new"
    assert captured["title"] == "Old Title"
    assert captured["content"] == "body"
    assert captured["description"] == "desc"
    assert captured["tags"] == ["notes"]
    assert result.previous_page == {"id": 42, "path": "ideas/old", "title": "Old Title"}
    assert result.changed["path"] is True
    assert result.changed["title"] is False


def test_move_page_raises_when_destination_exists(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_get(path):
        if path == "ideas/old":
            return PageDetail(id=42, path="ideas/old", title="Old Title", content="body", description="desc", tags=[])
        if path == "ideas/new":
            return PageDetail(id=99, path="ideas/new", title="New Title", content="body", description="desc", tags=[])
        return None

    monkeypatch.setattr(client, "get_page_by_path", fake_get)
    with pytest.raises(WikiJsError, match="Destination path already exists"):
        client.move_page(source_path="ideas/old", destination_path="ideas/new")


def test_move_page_rejects_same_source_and_destination(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: PageDetail(id=42, path="ideas/old", title="Old Title", content="body", description="desc", tags=[]))
    with pytest.raises(WikiJsError, match="source and destination paths are the same"):
        client.move_page(source_path=" ideas/old ", destination_path="/ideas/old/")


def test_create_page_rejects_empty_title():
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    with pytest.raises(WikiJsError, match="title must not be empty"):
        client.create_page(path="ideas/test", title="   ", content="# Test")


def test_create_page_rejects_zero_width_space_in_path():
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    with pytest.raises(WikiJsError, match=r"unsupported invisible character U\+200B"):
        client.create_page(path="ideas/\u200btest", title="Test", content="# Test")


def test_create_page_rejects_format_characters_in_title():
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    with pytest.raises(WikiJsError, match=r"unsupported formatting character U\+2060"):
        client.create_page(path="ideas/test", title="Test\u2060Title", content="# Test")


def test_create_page_allows_non_strict_description_formatting_chars():
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    captured = {}

    def fake_post(query, variables=None):
        captured.update(variables or {})
        return {"pages": {"create": {"responseResult": {"succeeded": True, "message": "ok", "errorCode": 0}, "page": {"id": 1, "path": "ideas/test", "title": "Test"}}}}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(client, "_post", fake_post)
    try:
        client.create_page(path="ideas/test", title="Test", content="# Test", description="desc\u2060ok")
    finally:
        monkeypatch.undo()
    assert captured["description"] == "desc\u2060ok"


def test_create_page_raises_conflict_error_on_duplicate_path(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(query, variables=None):
        return {
            "pages": {
                "create": {
                    "responseResult": {
                        "succeeded": False,
                        "message": "Page already exists at this path",
                        "errorCode": 409,
                    },
                    "page": None,
                }
            }
        }

    monkeypatch.setattr(client, "_post", fake_post)
    with pytest.raises(WikiJsConflictError, match=r"create failed: Page already exists at this path \(errorCode=409\)"):
        client.create_page(path="ideas/test", title="Test", content="# Test")


def test_update_page_raises_validation_error_on_invalid_payload(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(query, variables=None):
        return {
            "pages": {
                "update": {
                    "responseResult": {
                        "succeeded": False,
                        "message": "Title is required",
                        "errorCode": 400,
                    }
                }
            }
        }

    monkeypatch.setattr(client, "_post", fake_post)
    with pytest.raises(WikiJsValidationError, match=r"update failed: Title is required \(errorCode=400\)"):
        client.update_page(page_id=1, path="ideas/test", title="Test", content="# Test")


def test_delete_page_by_path_raises_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)

    try:
        client.delete_page_by_path("ideas/missing")
    except WikiJsError as exc:
        assert "No page found" in str(exc)
    else:
        raise AssertionError("Expected WikiJsError")


def test_delete_page_normalizes_path(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    seen = {}

    def fake_get(path):
        seen["path"] = path
        return None

    monkeypatch.setattr(client, "get_page_by_path", fake_get)
    with pytest.raises(WikiJsError, match="No page found"):
        client.delete_page_by_path(" /ideas/missing/ ")
    assert seen["path"] == "ideas/missing"


def test_delete_page_returns_previous_page_payload(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(
        client,
        "get_page_by_path",
        lambda path: PageDetail(id=3, path=path, title="Gone", content="body", description="desc", tags=[PageTag(tag="cleanup", title="Cleanup")]),
    )

    def fake_post(query, variables=None):
        return {"pages": {"delete": {"responseResult": {"succeeded": True, "message": "deleted", "errorCode": 0}}}}

    monkeypatch.setattr(client, "_post", fake_post)
    result = client.delete_page_by_path("ideas/gone")
    assert result.previous_page == {
        "id": 3,
        "path": "ideas/gone",
        "title": "Gone",
        "description": "desc",
        "tags": [{"tag": "cleanup", "title": "Cleanup"}],
    }
    assert result.changed["deleted"] is True


def test_delete_page_raises_conflict_error_when_api_reports_lock(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(
        client,
        "get_page_by_path",
        lambda path: PageDetail(id=3, path=path, title="Gone", content="body", description="desc", tags=[]),
    )

    def fake_post(query, variables=None):
        return {"pages": {"delete": {"responseResult": {"succeeded": False, "message": "Delete conflict: page is locked", "errorCode": 423}}}}

    monkeypatch.setattr(client, "_post", fake_post)
    with pytest.raises(WikiJsConflictError, match=r"delete failed: Delete conflict: page is locked \(errorCode=423\)"):
        client.delete_page_by_path("ideas/gone")


def test_update_page_rejects_zero_width_tag(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    with pytest.raises(WikiJsError, match=r"unsupported invisible character U\+200B"):
        client.update_page(page_id=1, path="ideas/test", title="Test", content="# Test", tags=["good", "\u200bbad"])


def test_post_wraps_request_exception(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(WikiJsError, match="Request to Wiki.js failed"):
        client._post("query { ping }")


def test_post_wraps_graphql_errors(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(*args, **kwargs):
        return DummyResponse({"errors": [{"message": "nope"}]})

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(WikiJsError, match=r"GraphQL error\(s\): nope"):
        client._post("query { ping }")


def test_post_rejects_missing_data_payload(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")

    def fake_post(*args, **kwargs):
        return DummyResponse({})

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(WikiJsError, match="did not include a data payload"):
        client._post("query { ping }")


def test_search_pages_raises_schema_error_when_results_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "_post", lambda query, variables=None: {"pages": {"search": {}}})
    with pytest.raises(WikiJsSchemaError, match="did not include pages.search.results"):
        client.search_pages(query="homeos")


def test_list_pages_raises_schema_error_when_list_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "_post", lambda query, variables=None: {"pages": {}})
    with pytest.raises(WikiJsSchemaError, match="did not include pages.list"):
        client.list_pages()


def test_list_pages_with_path_uses_search(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    captured = {}

    def fake_post(query, variables=None):
        captured["variables"] = variables
        return {"pages": {"search": {"results": [{"id": 7, "path": "ideas/homeos", "title": "HomeOS"}]}}}

    monkeypatch.setattr(client, "_post", fake_post)
    pages = client.list_pages(path="ideas")
    assert len(pages) == 1
    assert captured["variables"] == {"path": "ideas", "query": "", "locale": "en"}


def test_search_pages_uses_client_locale(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token", locale="fr")
    captured = {}

    def fake_post(query, variables=None):
        captured["query"] = query
        captured["variables"] = variables
        return {"pages": {"search": {"results": []}}}

    monkeypatch.setattr(client, "_post", fake_post)
    client.search_pages(query="bonjour")
    assert captured["variables"] == {"path": "", "query": "bonjour", "locale": "fr"}
