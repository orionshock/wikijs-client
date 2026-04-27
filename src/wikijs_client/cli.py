from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import __version__
from .client import (
    WikiJsAmbiguousMatchError,
    WikiJsClient,
    WikiJsConflictError,
    WikiJsError,
    WikiJsNotFoundError,
    WikiJsSchemaError,
    WikiJsValidationError,
)
from .models import PageSummary


TARGET_WIKIJS_VERSION = "2.5.312"
EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_NOT_FOUND = 2
EXIT_AMBIGUOUS = 3
EXIT_VALIDATION = 4


def _debug_emit(enabled: bool, message: str) -> None:
    if enabled:
        print(f"debug: {message}", file=sys.stderr)


def _sanitize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _summarize_args(args: argparse.Namespace) -> str:
    parts = []
    for key, value in sorted(vars(args).items()):
        if key in {"func", "debug"}:
            continue
        if value in (None, False):
            continue
        parts.append(f"{key}={value!r}")
    return ", ".join(parts) if parts else "(no options)"


def build_client(*, debug: bool = False) -> WikiJsClient:
    """Build a client from environment variables."""
    url = os.environ.get("WIKIJS_URL")
    token = os.environ.get("WIKIJS_TOKEN")
    locale = os.environ.get("WIKIJS_LOCALE", "en")
    if not url or not token:
        raise WikiJsValidationError("WIKIJS_URL and WIKIJS_TOKEN must be set")
    _debug_emit(debug, f"client config: url={_sanitize_url(url)} locale={locale}")
    return WikiJsClient(url=url, token=token, locale=locale, debug=(lambda message: _debug_emit(debug, message)))


def emit(data: Any) -> None:
    """Emit structured JSON output."""
    print(json.dumps(data, indent=2))


def emit_to_file(path: str, data: str) -> None:
    """Write command output to a file, creating parent directories when needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data)


def is_quiet(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "quiet", False))


def _page_identity_text(page: dict[str, Any] | None) -> str:
    if not page:
        return ""
    parts = []
    if page.get("id") is not None:
        parts.append(f"id {page['id']}")
    if page.get("path"):
        parts.append(f"path {page['path']}")
    if page.get("title") is not None:
        parts.append(f"title {page['title']!r}")
    return ", ".join(parts)


def truncate(value: str, width: int) -> str:
    """Truncate a string for compact human-readable table output."""
    if len(value) <= width:
        return value
    return value[: max(0, width - 1)] + "…"


def render_page_row(page: PageSummary) -> str:
    """Render a single page summary as a compact aligned row."""
    page_id = str(page.id)
    path = truncate(page.path, 42)
    title = truncate(page.title, 28)
    description = truncate(page.description, 36)
    return f"{page_id:>5}  {path:<42}  {title:<28}  {description}"


def _render_page_table(pages: list[PageSummary], *, as_json: bool) -> None:
    """Render page summaries as JSON or a compact human-readable table."""
    if as_json:
        emit([page.to_dict() for page in pages])
        return
    print(f"{'ID':>5}  {'PATH':<42}  {'TITLE':<28}  DESCRIPTION")
    print(f"{'-' * 5}  {'-' * 42}  {'-' * 28}  {'-' * 36}")
    for page in pages:
        print(render_page_row(page))
    print(f"\n{len(pages)} page(s)")


def run_versioncheck(*, as_json: bool, debug: bool) -> int:
    client = build_client(debug=debug)
    version = client.get_version(target_version=TARGET_WIKIJS_VERSION)
    payload = version.to_dict()
    if as_json:
        emit(payload)
    else:
        print(f"current: {payload['currentVersion'] or 'unknown'}")
        print(f"target: {payload['targetVersion']}")
        if payload["latestVersion"]:
            print(f"latest: {payload['latestVersion']}")
        if payload["latestVersionReleaseDate"]:
            print(f"latest release: {payload['latestVersionReleaseDate']}")
        if payload["upgradeCapable"] is not None:
            print(f"upgrade capable: {payload['upgradeCapable']}")
        if payload["matchesTarget"] is False:
            print(f"warning: expected {payload['targetVersion']}, got {payload['currentVersion'] or 'unknown'}")
        elif payload["matchesTarget"] is True:
            print("version check: ok")
    return EXIT_SUCCESS


def run_versioncheck_quiet(*, debug: bool) -> int:
    client = build_client(debug=debug)
    client.get_version(target_version=TARGET_WIKIJS_VERSION)
    return EXIT_SUCCESS


def cmd_list(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    pages = client.list_pages(query=args.query or "", path=args.path or "")
    if args.regex:
        pattern = re.compile(args.regex)
        pages = [p for p in pages if pattern.search(p.path) or pattern.search(p.title) or pattern.search(p.description)]
    if not is_quiet(args):
        _render_page_table(pages, as_json=args.json)
    return EXIT_SUCCESS


def cmd_search(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    pages = client.search_pages(query=args.text)
    if not is_quiet(args):
        _render_page_table(pages, as_json=args.json)
    return EXIT_SUCCESS


def cmd_exists(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    page = client.get_page_by_path(args.path)
    exists = page is not None
    if args.json:
        emit({"path": args.path, "exists": exists})
    elif not is_quiet(args):
        print(f"exists: {args.path}" if exists else f"missing: {args.path}")
    return EXIT_SUCCESS if exists else EXIT_NOT_FOUND


def cmd_get(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    page = client.get_page_by_path(args.path)
    if not page:
        print(f"No page found at path: {args.path}", file=sys.stderr)
        return EXIT_NOT_FOUND
    if args.json:
        payload = json.dumps(page.to_dict(), indent=2)
        if getattr(args, "file", None):
            emit_to_file(args.file, payload + "\n")
        else:
            print(payload)
    elif getattr(args, "file", None):
        emit_to_file(args.file, page.content)
    elif not is_quiet(args):
        print(page.content)
    return EXIT_SUCCESS


def cmd_upsert(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    if args.file:
        content = Path(args.file).read_text()
        content_source = "file"
    else:
        content = sys.stdin.read()
        content_source = "stdin"
    if args.dry_run:
        path = args.path
        title = args.title
        existing = client.get_page_by_path(path)
        description_preserved = bool(existing and args.description is None and not args.replace_description)
        tags_preserved = bool(existing and args.tags is None and not args.replace_tags)
        existing_tags = [t.tag for t in existing.tags if t.tag] if existing else []
        resolved_description = existing.description if description_preserved else (args.description or "")
        resolved_tags = existing_tags if tags_preserved else (args.tags or [])
        content_changed = True if not existing else existing.content != content
        title_changed = False if not existing else existing.title != title
        description_changed = bool(existing and (resolved_description != existing.description))
        tags_changed = bool(existing and (resolved_tags != existing_tags))
        change_summary = {
            "content": {
                "changed": content_changed,
                "oldChars": 0 if not existing else len(existing.content),
                "newChars": len(content),
                "oldLines": 0 if not existing else len(existing.content.splitlines()),
                "newLines": len(content.splitlines()),
            },
            "title": {
                "changed": title_changed,
            },
            "description": {
                "changed": description_changed,
                "preserved": description_preserved,
            },
            "tags": {
                "changed": tags_changed,
                "preserved": tags_preserved,
                "oldCount": len(existing_tags),
                "newCount": len(resolved_tags),
            },
        }
        payload = {
            "action": "update" if existing else "create",
            "dry_run": True,
            "wouldMutate": True,
            "target": {
                "path": path,
                "title": title,
            },
            "changed": {
                "content": content_changed,
                "title": title_changed,
                "description": description_changed,
                "tags": tags_changed,
                "created": not bool(existing),
                "updated": bool(existing),
                "deleted": False,
            },
            "metadata": {
                "description_preserved": description_preserved,
                "tags_preserved": tags_preserved,
                "content_source": content_source,
                "change_summary": change_summary,
            },
        }
        if existing:
            payload["resolvedPage"] = {
                "id": existing.id,
                "path": existing.path,
                "title": existing.title,
            }
        if args.diff:
            before_lines = [] if not existing else existing.content.splitlines(keepends=True)
            after_lines = content.splitlines(keepends=True)
            payload["diff"] = list(
                difflib.unified_diff(
                    before_lines,
                    after_lines,
                    fromfile=f"wiki:{path}" if existing else "/dev/null",
                    tofile=f"input:{path}",
                    lineterm="",
                )
            )
        if args.json:
            emit(payload)
        elif not is_quiet(args):
            details = []
            summary = payload["metadata"]["change_summary"]
            content_summary = summary["content"]
            if content_summary["changed"]:
                details.append(
                    f"content changed: {content_summary['oldChars']} -> {content_summary['newChars']} chars"
                )
            else:
                details.append("content unchanged")
            if summary["title"]["changed"]:
                details.append("title changed")
            else:
                details.append("title unchanged")
            if payload["metadata"]["description_preserved"]:
                details.append("description preserved")
            elif summary["description"]["changed"]:
                details.append("description changed")
            else:
                details.append("description unchanged")
            if payload["metadata"]["tags_preserved"]:
                details.append("tags preserved")
            elif summary["tags"]["changed"]:
                details.append(f"tags changed: {summary['tags']['oldCount']} -> {summary['tags']['newCount']}")
            else:
                details.append("tags unchanged")
            suffix = f" [{', '.join(details)}]" if details else ""
            if existing:
                print(f"dry-run: would update {path} (id {existing.id}, title {existing.title!r}){suffix}")
            else:
                print(f"dry-run: would create {path} with title {title!r}{suffix}")
            if args.diff:
                before_lines = [] if not existing else existing.content.splitlines(keepends=True)
                after_lines = content.splitlines(keepends=True)
                diff_lines = list(
                    difflib.unified_diff(
                        before_lines,
                        after_lines,
                        fromfile=f"wiki:{path}" if existing else "/dev/null",
                        tofile=f"input:{path}",
                        lineterm="",
                    )
                )
                if diff_lines:
                    print("\n" + "\n".join(diff_lines))
                else:
                    print("\n(no diff)")
        return EXIT_SUCCESS
    result = client.upsert_page(
        path=args.path,
        title=args.title,
        content=content,
        description=args.description,
        tags=args.tags,
        preserve_description=not args.replace_description,
        preserve_tags=not args.replace_tags,
    )
    if args.json:
        emit(result.to_dict())
    elif not is_quiet(args):
        result_payload = result.to_dict()
        response = result_payload.get("responseResult", {})
        page_identity = _page_identity_text(result_payload.get("page"))
        details = []
        metadata = result.metadata or {}
        if metadata.get("description_preserved"):
            details.append("description preserved")
        if metadata.get("tags_preserved"):
            details.append("tags preserved")
        if page_identity:
            details.insert(0, page_identity)
        suffix = f" [{', '.join(details)}]" if details else ""
        print(f"{result.action}: {args.path} ({response.get('message', 'ok')}){suffix}")
    return EXIT_SUCCESS


def cmd_delete(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    if args.dry_run:
        existing = client.get_page_by_path(args.path)
        payload = {
            "action": "delete",
            "dry_run": True,
            "wouldMutate": bool(existing),
            "target": {
                "path": args.path,
            },
            "changed": {
                "created": False,
                "updated": False,
                "deleted": bool(existing),
            },
            "metadata": {
                "found": bool(existing),
            },
        }
        if existing:
            payload["resolvedPage"] = {
                "id": existing.id,
                "path": existing.path,
                "title": existing.title,
            }
        if args.json:
            emit(payload)
        elif not is_quiet(args):
            if existing:
                print(f"dry-run: would delete {existing.path} (id {existing.id}, title {existing.title!r})")
            else:
                print(f"dry-run: would not delete {args.path} (page not found)")
        return EXIT_SUCCESS
    if not getattr(args, "force", False):
        raise WikiJsValidationError("delete requires --force; use --dry-run to preview")
    result = client.delete_page_by_path(args.path)
    if args.json:
        emit(result.to_dict())
    elif not is_quiet(args):
        result_payload = result.to_dict()
        response = result_payload.get("responseResult", {})
        page_identity = _page_identity_text(result_payload.get("page") or result_payload.get("resolvedPage"))
        suffix = f" [{page_identity}]" if page_identity else ""
        print(f"deleted: {args.path} ({response.get('message', 'ok')}){suffix}")
    return EXIT_SUCCESS


def cmd_move(args: argparse.Namespace) -> int:
    client = build_client(debug=getattr(args, "debug", False))
    if args.dry_run:
        existing = client.get_page_by_path(args.source_path)
        destination_existing = client.get_page_by_path(args.destination_path)
        resolved_title = args.title if args.title is not None else (existing.title if existing else None)
        destination_conflict = bool(existing and destination_existing and destination_existing.id != existing.id)
        source_found = bool(existing)
        path_changed = bool(existing and existing.path != args.destination_path)
        title_changed = bool(existing and resolved_title is not None and existing.title != resolved_title)
        would_mutate = bool(source_found and not destination_conflict and (path_changed or title_changed))
        payload = {
            "action": "move",
            "dry_run": True,
            "wouldMutate": would_mutate,
            "target": {
                "source_path": args.source_path,
                "destination_path": args.destination_path,
                "title": resolved_title,
            },
            "changed": {
                "created": False,
                "updated": would_mutate,
                "deleted": False,
                "path": path_changed,
                "title": title_changed,
            },
            "metadata": {
                "source_found": source_found,
                "destination_exists": bool(destination_existing),
                "destination_conflict": destination_conflict,
            },
        }
        if existing:
            payload["resolvedPage"] = {
                "id": existing.id,
                "path": existing.path,
                "title": existing.title,
            }
        if destination_existing:
            payload["destinationPage"] = {
                "id": destination_existing.id,
                "path": destination_existing.path,
                "title": destination_existing.title,
            }
        if args.json:
            emit(payload)
        elif not is_quiet(args):
            title_note = f", title {resolved_title!r}" if resolved_title is not None else ""
            if not existing:
                print(f"dry-run: would not move {args.source_path} (page not found)")
            elif destination_conflict:
                print(
                    f"dry-run: would not move {existing.path} -> {args.destination_path} "
                    f"(destination exists: id {destination_existing.id}, title {destination_existing.title!r})"
                )
            elif would_mutate:
                print(
                    f"dry-run: would move {existing.path} -> {args.destination_path} "
                    f"(id {existing.id}, title {existing.title!r}{title_note})"
                )
            else:
                print(
                    f"dry-run: would not move {existing.path} "
                    f"(no change; id {existing.id}, title {existing.title!r})"
                )
        return EXIT_SUCCESS
    result = client.move_page(source_path=args.source_path, destination_path=args.destination_path, title=args.title)
    if args.json:
        emit(result.to_dict())
    elif not is_quiet(args):
        result_payload = result.to_dict()
        response = result_payload.get("responseResult", {})
        page_identity = _page_identity_text(result_payload.get("page"))
        suffix = f" [{page_identity}]" if page_identity else ""
        print(f"moved: {args.source_path} -> {args.destination_path} ({response.get('message', 'ok')}){suffix}")
    return EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wikijs-client",
        description=(
            f"wikijs-client {__version__}\n\n"
            "Practical Wiki.js GraphQL CLI with separate commands for exact existence checks, "
            "global search, and predictable list-based browsing. Use --json to emit structured output.\n"
            "Use '<command> --help' for command-specific arguments and examples."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--versioncheck", action="store_true", help=f"check the server version against the project target ({TARGET_WIKIJS_VERSION})")
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of human-readable output")
    parser.add_argument("--quiet", action="store_true", help="suppress successful stdout output; errors still go to stderr")
    parser.add_argument("--debug", action="store_true", help="emit debug details to stderr without contaminating stdout")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser(
        "list",
        help="list pages for browsing or server-backed discovery",
        description="List pages using pages.list() when called without filters. Use --query to pass text into Wiki.js search, --path to scope search by path, and --regex for optional local post-filtering.",
    )
    p_list.add_argument("--query", help="text to pass to Wiki.js search query")
    p_list.add_argument("--path", help="path to pass to Wiki.js search for scoped discovery")
    p_list.add_argument("--regex", help="regular expression filter across returned path, title, and description")
    p_list.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_list.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_list.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser(
        "search",
        help="search pages globally by text using Wiki.js search results",
        description="Search pages using pages.search(path='', query=TEXT). This is the preferred global text search command when you want ranked search results rather than full-wiki list filtering.",
    )
    p_search.add_argument("text", help="search text to send to Wiki.js search")
    p_search.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_search.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_search.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_search.set_defaults(func=cmd_search)

    p_exists = sub.add_parser(
        "exists",
        help="check whether a page exists at an exact path",
        description="Check whether a page exists at an exact path. This prefers targeted lookup, but verifies exact matches safely and falls back to full page listing when Wiki.js search results are stale or inconsistent.",
    )
    p_exists.add_argument("path", help="exact page path to check")
    p_exists.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_exists.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_exists.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_exists.set_defaults(func=cmd_exists)

    p_get = sub.add_parser(
        "get",
        help="fetch page content by exact path",
        description="Fetch page content by exact path using the same verified exact-path lookup flow as the exists command.",
    )
    p_get.add_argument("path")
    p_get.add_argument("--file", help="write fetched output to a file instead of stdout")
    p_get.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_get.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_get.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_get.set_defaults(func=cmd_get)

    p_upsert = sub.add_parser(
        "upsert",
        help="create a page when missing or update it when present",
        description="Create a page when it does not exist, or update it when it does. Use --dry-run to preview the action without mutating; add --diff to include a unified diff in the dry-run output.",
    )
    p_upsert.add_argument("path")
    p_upsert.add_argument("title")
    p_upsert.add_argument("--file")
    p_upsert.add_argument("--description")
    p_upsert.add_argument("--tags", nargs="*")
    p_upsert.add_argument("--replace-description", action="store_true", help="replace existing description instead of preserving it when omitted")
    p_upsert.add_argument("--replace-tags", action="store_true", help="replace existing tags instead of preserving them when omitted")
    p_upsert.add_argument("--dry-run", action="store_true", help="preview whether upsert would create or update without mutating")
    p_upsert.add_argument("--diff", action="store_true", help="with --dry-run, include a unified diff of content changes")
    p_upsert.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_upsert.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_upsert.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_upsert.set_defaults(func=cmd_upsert)

    p_delete = sub.add_parser("delete", help="delete a page by exact path")
    p_delete.add_argument("path")
    p_delete.add_argument("--dry-run", action="store_true")
    p_delete.add_argument("--force", action="store_true", help="confirm and perform the delete")
    p_delete.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_delete.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_delete.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_delete.set_defaults(func=cmd_delete)

    p_move = sub.add_parser("move", help="move or rename a page by exact path")
    p_move.add_argument("source_path")
    p_move.add_argument("destination_path")
    p_move.add_argument("--title", help="optional new title; defaults to the existing title")
    p_move.add_argument("--dry-run", action="store_true")
    p_move.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_move.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_move.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p_move.set_defaults(func=cmd_move)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "json", False) and getattr(args, "quiet", False):
        parser.error("--quiet and --json cannot be used together")
    try:
        if args.versioncheck:
            _debug_emit(args.debug, f"command=versioncheck args={_summarize_args(args)}")
            if args.quiet:
                return run_versioncheck_quiet(debug=args.debug)
            return run_versioncheck(as_json=args.json, debug=args.debug)
        if not hasattr(args, "func"):
            parser.error("a command is required unless --versioncheck is used")
        _debug_emit(args.debug, f"command={args.command} args={_summarize_args(args)}")
        return args.func(args)
    except WikiJsNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    except WikiJsAmbiguousMatchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_AMBIGUOUS
    except (WikiJsValidationError, WikiJsConflictError, WikiJsSchemaError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except WikiJsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_GENERAL_FAILURE
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return EXIT_VALIDATION


if __name__ == "__main__":
    raise SystemExit(main())
