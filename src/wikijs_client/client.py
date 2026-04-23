from __future__ import annotations

import json
import os
import unicodedata
from dataclasses import dataclass
from typing import Any

import requests

from .models import MutationResult, PageDetail, PageSummary


class WikiJsError(RuntimeError):
    """Raised when the Wiki.js API returns an unusable or failed response."""


class WikiJsSchemaError(WikiJsError):
    """Raised when the Wiki.js schema is missing fields or shapes the client expects."""


KNOWN_BAD_INVISIBLES = {
    "\ufeff",
    "\u200b",
}


def _reject_unsupported_chars(value: str, field_name: str, *, strict: bool = False) -> str:
    for ch in value:
        category = unicodedata.category(ch)
        codepoint = f"U+{ord(ch):04X}"
        if category == "Cc" and ch not in "\t\n\r":
            raise WikiJsError(f"{field_name} contains unsupported control character {codepoint}")
        if ch == "\x7f" or category == "Cs":
            raise WikiJsError(f"{field_name} contains unsupported control character {codepoint}")
        if ch in KNOWN_BAD_INVISIBLES:
            raise WikiJsError(f"{field_name} contains unsupported invisible character {codepoint}")
        if strict and category == "Cf":
            raise WikiJsError(f"{field_name} contains unsupported formatting character {codepoint}")
    return value


def _normalize_path(path: str) -> str:
    path = _reject_unsupported_chars(path.strip(), "path", strict=True)
    if not path:
        raise WikiJsError("path must not be empty")
    path = path.strip("/")
    path = "/".join(part.strip() for part in path.split("/") if part.strip())
    if not path:
        raise WikiJsError("path must not be empty")
    return path


def _normalize_title(title: str) -> str:
    title = _reject_unsupported_chars(title.strip(), "title", strict=True)
    if not title:
        raise WikiJsError("title must not be empty")
    return title


def _normalize_description(description: str | None) -> str:
    if description is None:
        return ""
    return _reject_unsupported_chars(description.strip(), "description", strict=False)


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    normalized = []
    for tag in tags:
        clean = _reject_unsupported_chars(tag.strip(), "tag", strict=True)
        if clean:
            normalized.append(clean)
    return normalized


@dataclass
class WikiJsClient:
    """Minimal Wiki.js GraphQL client focused on practical page operations.

    Public methods are intended to be reusable by scripts, tools, and future adapters:
    - list_pages()
    - search_pages(query, path="")
    - get_page_by_path(path)
    - create_page(...)
    - update_page(...)
    - upsert_page(...)
    - move_page(...)
    - delete_page_by_path(path)

    Private helpers prefixed with `_` are internal and should not be treated as stable API.
    """

    url: str
    token: str
    timeout: int = 30
    locale: str = "en"

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

    def list_pages(self, *, query: str = "", path: str = "") -> list[PageSummary]:
        """Return pages as normalized PageSummary objects.

        With no arguments, this returns the full `pages.list()` inventory.
        With `query` or `path`, this uses Wiki.js `pages.search(...)` so callers can
        discover pages by server-backed text or subtree-style path input.
        """
        query_text = _reject_unsupported_chars(query.strip(), "query", strict=False)
        path_value = _normalize_path(path) if path.strip() else ""
        if not query_text and not path_value:
            gql = """
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
            try:
                data = self._post(gql)
                items = data["pages"]["list"]
            except KeyError as exc:
                raise WikiJsSchemaError("Wiki.js response did not include pages.list; this deployment may not support list-based browsing") from exc
            return [PageSummary.from_api(item) for item in items]
        return self.search_pages(query=query_text, path=path_value)

    def _find_single_exact_match(self, results: list[PageSummary], *, path: str, source: str) -> PageSummary | None:
        exact_matches = [page for page in results if page.path == path]
        if not exact_matches:
            return None
        if len(exact_matches) > 1:
            ids = ", ".join(str(page.id) for page in exact_matches)
            raise WikiJsError(f"Multiple pages matched path exactly via {source}: {path} (ids: {ids})")
        return exact_matches[0]

    def _find_page_summary_by_path_via_list(self, path: str) -> PageSummary | None:
        """Exact path lookup using pages.list() plus client-side filtering."""
        return self._find_single_exact_match(self.list_pages(), path=path, source="pages.list")

    def _find_page_summary_by_path_via_search(self, path: str) -> PageSummary | None:
        """Use pages.search for targeted path lookup with exact-match filtering."""
        results = self.search_pages(query="", path=path)
        return self._find_single_exact_match(results, path=path, source="pages.search")

    def search_pages(self, *, query: str, path: str = "") -> list[PageSummary]:
        """Search pages and return normalized PageSummary results.

        Args:
            query: Text to send to Wiki.js search.
            path: Optional path input passed through to Wiki.js search. An empty
                string performs global search on the current tested Wiki.js setup.

        Returns:
            A list of PageSummary results in server-returned order.

        Notes:
            Search behavior and ranking come from the Wiki.js server. Callers should
            not assume subtree semantics from `path` unless they have validated that
            behavior on their target Wiki.js instance.
        """
        query_text = _reject_unsupported_chars(query.strip(), "query", strict=False)
        path_value = _normalize_path(path) if path.strip() else ""
        gql = """
        query ($path: String!, $query: String!, $locale: String!) {
          pages {
            search(path: $path, locale: $locale, query: $query) {
              results {
                id
                path
                title
              }
            }
          }
        }
        """
        try:
            data = self._post(gql, {"path": path_value, "query": query_text, "locale": self.locale})
            items = data["pages"]["search"]["results"]
        except KeyError as exc:
            raise WikiJsSchemaError("Wiki.js response did not include pages.search.results; this deployment may not support the expected search schema") from exc
        return [PageSummary.from_api(item) for item in items]

    def _get_page_by_id(self, page_id: int) -> PageDetail:
        """Fetch a detailed page object by id."""
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
        try:
            data = self._post(query, {"id": page_id})
            payload = data["pages"]["single"]
        except KeyError as exc:
            raise WikiJsSchemaError("Wiki.js response did not include pages.single; this deployment may not support the expected page detail schema") from exc
        return PageDetail.from_api(payload)

    def get_page_by_path(self, path: str) -> PageDetail | None:
        """Return a detailed page by exact path, or None if it does not exist.

        The path is normalized before lookup. Exact lookup uses targeted
        `pages.search(...)` plus exact client-side filtering, followed by
        `pages.single(id: ...)` for the full page payload.
        """
        path = _normalize_path(path)
        match = self._find_page_summary_by_path_via_search(path)
        if match is None:
            return None
        return self._get_page_by_id(match.id)

    def create_page(self, *, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> MutationResult:
        """Create a page and return a normalized MutationResult.

        Inputs are normalized before the GraphQL mutation is sent.
        """
        path = _normalize_path(path)
        title = _normalize_title(title)
        description = _normalize_description(description)
        tags = _normalize_tags(tags)
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
            "tags": tags,
        })
        result = data["pages"]["create"]
        response = result["responseResult"]
        return MutationResult(
            action="created",
            succeeded=bool(response.get("succeeded")),
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
            page=result.get("page"),
            changed={
                "created": bool(response.get("succeeded")),
                "updated": False,
                "deleted": False,
            },
        )

    def update_page(self, *, page_id: int, path: str, title: str, content: str, description: str = "", tags: list[str] | None = None) -> MutationResult:
        """Update a page by id and return a normalized MutationResult."""
        path = _normalize_path(path)
        title = _normalize_title(title)
        description = _normalize_description(description)
        tags = _normalize_tags(tags)
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
            "tags": tags,
        })
        result = data["pages"]["update"]
        response = result["responseResult"]
        return MutationResult(
            action="updated",
            succeeded=bool(response.get("succeeded")),
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
            page={"id": page_id, "path": path, "title": title},
            changed={
                "created": False,
                "updated": bool(response.get("succeeded")),
                "deleted": False,
            },
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
        """Create or update a page while preserving metadata by default on update.

        When updating an existing page, description and tags are preserved unless
        explicit replacement values are provided or preservation is disabled.
        """
        path = _normalize_path(path)
        title = _normalize_title(title)
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
            existing_tags_payload = [tag.to_dict() for tag in existing.tags]
            updated_tags_payload = [{"tag": tag, "title": ""} for tag in resolved_tags]
            return MutationResult(
                action="updated",
                succeeded=result.succeeded,
                message=result.message,
                error_code=result.error_code,
                page={
                    "id": existing.id,
                    "path": path,
                    "title": title,
                    "description": resolved_description,
                    "tags": updated_tags_payload,
                },
                previous_page={
                    "id": existing.id,
                    "path": existing.path,
                    "title": existing.title,
                    "description": existing.description,
                    "tags": existing_tags_payload,
                },
                changed={
                    "created": False,
                    "updated": result.succeeded,
                    "deleted": False,
                    "title": existing.title != title,
                    "description": existing.description != resolved_description,
                    "tags": existing_tags != resolved_tags,
                    "content": existing.content != content,
                },
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

    def move_page(self, *, source_path: str, destination_path: str, title: str | None = None) -> MutationResult:
        """Move or rename a page by updating its path and optionally its title."""
        source_path = _normalize_path(source_path)
        destination_path = _normalize_path(destination_path)
        existing = self.get_page_by_path(source_path)
        if not existing:
            raise WikiJsError(f"No page found at path: {source_path}")
        if source_path == destination_path and title is None:
            raise WikiJsError("source and destination paths are the same")
        destination_existing = self.get_page_by_path(destination_path)
        if destination_existing and destination_existing.id != existing.id:
            raise WikiJsError(f"Destination path already exists: {destination_path}")
        result = self.update_page(
            page_id=existing.id,
            path=destination_path,
            title=_normalize_title(title) if title is not None else existing.title,
            content=existing.content,
            description=existing.description,
            tags=[t.tag for t in existing.tags if t.tag],
        )
        return MutationResult(
            action="moved",
            succeeded=result.succeeded,
            message=result.message,
            error_code=result.error_code,
            page={"id": existing.id, "path": destination_path, "title": title or existing.title},
            previous_page={"id": existing.id, "path": existing.path, "title": existing.title},
            changed={
                "created": False,
                "updated": result.succeeded,
                "deleted": False,
                "path": existing.path != destination_path,
                "title": existing.title != (title or existing.title),
            },
            metadata={"source_path": source_path, "destination_path": destination_path},
        )

    def delete_page_by_path(self, path: str) -> MutationResult:
        """Delete a page by exact path and return a normalized MutationResult."""
        path = _normalize_path(path)
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
        succeeded = bool(response.get("succeeded"))
        return MutationResult(
            action="deleted",
            succeeded=succeeded,
            message=response.get("message") or "",
            error_code=response.get("errorCode"),
            previous_page={
                "id": existing.id,
                "path": existing.path,
                "title": existing.title,
                "description": existing.description,
                "tags": [tag.to_dict() for tag in existing.tags],
            },
            changed={
                "created": False,
                "updated": False,
                "deleted": succeeded,
            },
        )
