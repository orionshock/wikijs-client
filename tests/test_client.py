from __future__ import annotations

from wikijs_graphql_tool.client import WikiJsClient, WikiJsError


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

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
        return {"pages": {"single": {"id": 7, "path": "ideas/homeos", "title": "HomeOS", "content": "body", "description": "desc"}}}

    monkeypatch.setattr(client, "_post", fake_post)
    page = client.get_page_by_path("ideas/homeos")
    assert page is not None
    assert page["content"] == "body"
    assert len(calls) == 2
    assert calls[1][1] == {"id": 7}


def test_upsert_page_creates_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)
    monkeypatch.setattr(
        client,
        "create_page",
        lambda **kwargs: {"responseResult": {"succeeded": True, "message": "Page created successfully.", "errorCode": 0}, "page": {"id": 1, "path": kwargs["path"], "title": kwargs["title"]}},
    )

    result = client.upsert_page(path="ideas/test", title="Test", content="# Test")
    assert result["action"] == "created"
    assert result["responseResult"]["succeeded"] is True


def test_upsert_page_updates_when_existing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: {"id": 99, "path": path, "title": "Old"})
    monkeypatch.setattr(
        client,
        "update_page",
        lambda **kwargs: {"responseResult": {"succeeded": True, "message": "Page has been updated.", "errorCode": 0}},
    )

    result = client.upsert_page(path="ideas/test", title="Test", content="# Test")
    assert result["action"] == "updated"
    assert result["responseResult"]["succeeded"] is True


def test_delete_page_by_path_raises_when_missing(monkeypatch):
    client = WikiJsClient(url="https://example.invalid/graphql", token="token")
    monkeypatch.setattr(client, "get_page_by_path", lambda path: None)

    try:
        client.delete_page_by_path("ideas/missing")
    except WikiJsError as exc:
        assert "No page found" in str(exc)
    else:
        raise AssertionError("Expected WikiJsError")
