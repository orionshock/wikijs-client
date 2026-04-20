from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


class WikiJsError(RuntimeError):
    pass


@dataclass
class WikiJsClient:
    url: str
    token: str
    timeout: int = 30

    def _post(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.post(
                self.url,
                json={"query": query, "variables": variables or {}},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WikiJsError(f"Request to Wiki.js failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise WikiJsError("Wiki.js returned a non-JSON response") from exc

        if payload.get("errors"):
            messages = []
            for err in payload["errors"]:
                if isinstance(err, dict):
                    messages.append(err.get("message", json.dumps(err, sort_keys=True)))
                else:
                    messages.append(str(err))
            raise WikiJsError("GraphQL error(s): " + "; ".join(messages))

        data = payload.get("data")
        if data is None:
            raise WikiJsError("Wiki.js response did not include a data payload")
        return data

    def list_pages(self) -> list[dict[str, Any]]:
        query = """
        query {
          pages {
            list(orderBy: PATH) {
              id
              path
              title
              description
            }
          }
        }
        """
        data = self._post(query)
        return data["pages"]["list"]

    def get_page_by_path(self, path: str) -> dict[str, Any] | None:
        pages = self.list_pages()
        match = next((p for p in pages if p["path"] == path), None)
        if not match:
            return None
        query = """
        query ($id: Int!) {
          pages {
            single(id: $id) {
              id
              path
              title
              content
              description
              tags {
                tag
                title
              }
            }
          }
        }
        """
        data = self._post(query, {"id": match["id"]})
        return data["pages"]["single"]

    def create_page(self, *, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        mutation = """
        mutation ($content: String!, $description: String!, $path: String!, $title: String!, $tags: [String!]!) {
          pages {
            create(
              content: $content
              description: $description
              editor: "markdown"
              isPublished: true
              isPrivate: false
              locale: "en"
              path: $path
              tags: $tags
              title: $title
            ) {
              responseResult {
                succeeded
                message
                errorCode
              }
              page {
                id
                path
                title
              }
            }
          }
        }
        """
        data = self._post(mutation, {
            "content": content,
            "description": description,
            "path": path,
            "title": title,
            "tags": tags or [],
        })
        return data["pages"]["create"]

    def update_page(self, *, page_id: int, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        mutation = """
        mutation ($id: Int!, $content: String!, $description: String!, $path: String!, $title: String!, $tags: [String!]) {
          pages {
            update(
              id: $id
              content: $content
              description: $description
              editor: "markdown"
              isPublished: true
              isPrivate: false
              locale: "en"
              path: $path
              tags: $tags
              title: $title
            ) {
              responseResult {
                succeeded
                message
                errorCode
              }
            }
          }
        }
        """
        data = self._post(mutation, {
            "id": page_id,
            "content": content,
            "description": description,
            "path": path,
            "title": title,
            "tags": tags or [],
        })
        return data["pages"]["update"]

    def upsert_page(
        self,
        *,
        path: str,
        title: str,
        content: str,
        description: str | None = None,
        tags: list[str] | None = None,
        preserve_description: bool = True,
        preserve_tags: bool = True,
    ) -> dict[str, Any]:
        existing = self.get_page_by_path(path)
        if existing:
            resolved_description = existing.get("description", "") if description is None and preserve_description else (description or "")
            existing_tags = [t.get("tag") for t in existing.get("tags", []) if isinstance(t, dict) and t.get("tag")]
            resolved_tags = existing_tags if tags is None and preserve_tags else (tags or [])
            result = self.update_page(
                page_id=existing["id"],
                path=path,
                title=title,
                content=content,
                description=resolved_description,
                tags=resolved_tags,
            )
            return {
                "action": "updated",
                "metadata": {
                    "description_preserved": description is None and preserve_description,
                    "tags_preserved": tags is None and preserve_tags,
                },
                **result,
            }
        result = self.create_page(
            path=path,
            title=title,
            content=content,
            description=description or "",
            tags=tags,
        )
        return {"action": "created", **result}

    def delete_page_by_path(self, path: str) -> dict[str, Any]:
        existing = self.get_page_by_path(path)
        if not existing:
            raise WikiJsError(f"No page found at path: {path}")
        mutation = """
        mutation ($id: Int!) {
          pages {
            delete(id: $id) {
              responseResult {
                succeeded
                message
                errorCode
              }
            }
          }
        }
        """
        data = self._post(mutation, {"id": existing["id"]})
        return data["pages"]["delete"]
