from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PageSummary:
    """Small, stable representation of a page in list output and lookup flows."""

    id: int
    path: str
    title: str
    description: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "PageSummary":
        return cls(
            id=int(data["id"]),
            path=data["path"],
            title=data.get("title") or "",
            description=data.get("description") or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PageTag:
    """Normalized tag representation returned by Wiki.js page detail queries."""

    tag: str
    title: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "PageTag":
        return cls(tag=data.get("tag") or "", title=data.get("title") or "")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PageDetail:
    """Detailed page representation for read/update flows."""

    id: int
    path: str
    title: str
    content: str
    description: str = ""
    tags: list[PageTag] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "PageDetail":
        return cls(
            id=int(data["id"]),
            path=data["path"],
            title=data.get("title") or "",
            content=data.get("content") or "",
            description=data.get("description") or "",
            tags=[PageTag.from_api(t) for t in data.get("tags") or []],
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = [tag.to_dict() for tag in self.tags]
        return payload


@dataclass(frozen=True)
class SiteVersion:
    """Compact version/status view returned by Wiki.js system info queries."""

    current_version: str = ""
    latest_version: str = ""
    latest_version_release_date: str = ""
    upgrade_capable: bool | None = None
    target_version: str = ""
    matches_target: bool | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any], *, target_version: str = "") -> "SiteVersion":
        current_version = data.get("currentVersion") or ""
        latest_version = data.get("latestVersion") or ""
        latest_version_release_date = data.get("latestVersionReleaseDate") or ""
        upgrade_capable = data.get("upgradeCapable")
        target_version = target_version.strip()
        matches_target = None if not target_version else current_version == target_version
        return cls(
            current_version=current_version,
            latest_version=latest_version,
            latest_version_release_date=latest_version_release_date,
            upgrade_capable=upgrade_capable,
            target_version=target_version,
            matches_target=matches_target,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "currentVersion": self.current_version,
            "latestVersion": self.latest_version,
            "latestVersionReleaseDate": self.latest_version_release_date,
            "upgradeCapable": self.upgrade_capable,
            "targetVersion": self.target_version,
            "matchesTarget": self.matches_target,
        }


@dataclass(frozen=True)
class MutationResult:
    """Normalized mutation result with optional metadata for human/automation output."""

    action: str
    succeeded: bool
    message: str = ""
    error_code: int | None = None
    page: dict[str, Any] | None = None
    target: dict[str, Any] | None = None
    resolved_page: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_page: dict[str, Any] | None = None
    changed: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "responseResult": {
                "succeeded": self.succeeded,
                "message": self.message,
                "errorCode": self.error_code,
            },
        }
        if self.page is not None:
            payload["page"] = self.page
        if self.target is not None:
            payload["target"] = self.target
        if self.resolved_page is not None:
            payload["resolvedPage"] = self.resolved_page
        if self.previous_page is not None:
            payload["previousPage"] = self.previous_page
        if self.changed:
            payload["changed"] = self.changed
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload
