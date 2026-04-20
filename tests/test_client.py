from __future__ import annotations

import pytest
import requests

from wikijs_graphql_tool.client import WikiJsClient, WikiJsError
from wikijs_graphql_tool.models import MutationResult, PageDetail, PageTag


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
        assert "list(orderBy: PATH)" in query
        return {"pages": {"list": [{"id": 1, "path": "foo", "title": "Foo", "description": ""}]}}

    monkeypatch.setattr(client, "_post", fake_post)
    assert client.get_page_by_path("bar") is None


def test_get_page_by_path_fetches_single_page(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    calls = []

    def fake_post(query, variables=None):
        calls.append((query, variables))
        if "list(orderBy: PATH)" in query:
            return {"pages": {"list": [{"id": 7, "path": "ideas/homeos", "title": "HomeOS", "description": ""}]}}
        return {"pages": {"single": {"id": 7, "path": "ideas/homeos", "title": "HomeOS", "content": "body", "description": "desc", "tags": [{"tag": "ideas", "title": "ideas"}]}}}

    monkeypatch.setattr(client, "_post", fake_post)
    page = client.get_page_by_path("ideas/homeos")
    assert page is not None
    assert page.content == "body"
    assert isinstance(page, PageDetail)
    assert len(calls) == 2
    assert calls[1][1] == {"id": 7}


def test_upsert_page_creates_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)
    monkeypatch.setattr(
        client,
        "create_page",
        lambda **kwargs: MutationResult(action="created", succeeded=True, message="Page created successfully.", error_code=0, page={"id": 1, "path": kwargs["path"], "title": kwargs["title"]}),
    )

    result = client.upsert_page(path="ideas/test", title="Test", content="# Test")
    assert result.action == "created"
    assert result.succeeded is True


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


def test_delete_page_by_path_raises_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)

    try:
        client.delete_page_by_path("ideas/missing")
    except WikiJsError as exc:
        assert "No page found" in str(exc)
    else:
        raise AssertionError("Expected WikiJsError")


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
