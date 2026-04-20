from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from .models import MutationResult, PageDetail, PageSummary


class WikiJsError(RuntimeError):
    """Raised when the Wiki.js API returns an unusable or failed response."""


@dataclass
class WikiJsClient:
    """Minimal Wiki.js GraphQL client focused on practical page operations."""

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

    def list_pages(self) -> list[PageSummary]:
        """Return page summaries suitable for listing and simple lookups."""
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
        return [PageSummary.from_api(item) for item in data["pages"]["list"]]

    def get_page_by_path(self, path: str) -> PageDetail | None:
        """Return a detailed page object by path, or None if it does not exist."""
        pages = self.list_pages()
        match = next((p for p in pages if p.path == path), None)
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
        data = self._post(query, {"id": match.id})
        return PageDetail.from_api(data["pages"]["single"])

    def create_page(self, *, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> MutationResult:
        """Create a page and return a normalized mutation result."""
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
        result = data["pages"]["create"]
        response = result["responseResult"]
        return MutationResult(
            action="created",
            succeeded=bool(response.get("succeeded")),
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
            page=result.get("page"),
        )

    def update_page(self, *, page_id: int, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> MutationResult:
        """Update a page and return a normalized mutation result."""
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
        result = data["pages"]["update"]
        response = result["responseResult"]
        return MutationResult(
            action="updated",
            succeeded=bool(response.get("succeeded")),
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
        )

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
    ) -> MutationResult:
        """Create or update a page while preserving metadata by default on update."""
        existing = self.get_page_by_path(path)
        if existing:
            resolved_description = existing.description if description is None and preserve_description else (description or "")
            existing_tags = [t.tag for t in existing.tags if t.tag]
            resolved_tags = existing_tags if tags is None and preserve_tags else (tags or [])
            result = self.update_page(
                page_id=existing.id,
                path=path,
                title=title,
                content=content,
                description=resolved_description,
                tags=resolved_tags,
            )
            return MutationResult(
                action="updated",
                succeeded=result.succeeded,
                message=result.message,
                error_code=result.error_code,
                page=result.page,
                metadata={
                    "description_preserved": description is None and preserve_description,
                    "tags_preserved": tags is None and preserve_tags,
                },
            )
        return self.create_page(
            path=path,
            title=title,
            content=content,
            description=description or "",
            tags=tags,
        )

    def delete_page_by_path(self, path: str) -> MutationResult:
        """Delete a page by path and return a normalized mutation result."""
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
        data = self._post(mutation, {"id": existing.id})
        result = data["pages"]["delete"]
        response = result["responseResult"]
        return MutationResult(
            action="deleted",
            succeeded=bool(response.get("succeeded")),
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
        )
