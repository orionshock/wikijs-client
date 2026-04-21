from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .client import WikiJsClient, WikiJsError
from .models import PageSummary


def build_client() -> WikiJsClient:
    """Build a client from environment variables."""
    url = os.environ.get("WIKIJS_URL")
    token = os.environ.get("WIKIJS_TOKEN")
    if not url or not token:
        raise WikiJsError("WIKIJS_URL and WIKIJS_TOKEN must be set")
    return WikiJsClient(url=url, token=token)


def emit(data: Any, *, as_json: bool) -> None:
    """Emit structured output when JSON mode is requested."""
    if as_json:
        print(json.dumps(data, indent=2))


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


def cmd_list(args: argparse.Namespace) -> int:
    client = build_client()
    pages = client.list_pages()
    if args.prefix:
        pages = [p for p in pages if p.path.startswith(args.prefix)]
    if args.query:
        needle = args.query.lower()
        pages = [p for p in pages if needle in (p.path.lower() + "\n" + p.title.lower() + "\n" + p.description.lower())]
    if args.regex:
        pattern = re.compile(args.regex)
        pages = [p for p in pages if pattern.search(p.path) or pattern.search(p.title) or pattern.search(p.description)]
    if args.json:
        emit([page.to_dict() for page in pages], as_json=True)
    else:
        print(f"{'ID':>5}  {'PATH':<42}  {'TITLE':<28}  DESCRIPTION")
        print(f"{'-' * 5}  {'-' * 42}  {'-' * 28}  {'-' * 36}")
        for page in pages:
            print(render_page_row(page))
        print(f"\n{len(pages)} page(s)")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    client = build_client()
    page = client.get_page_by_path(args.path)
    if not page:
        print(f"No page found at path: {args.path}", file=sys.stderr)
        return 1
    if args.json:
        emit(page.to_dict(), as_json=True)
    else:
        print(page.content)
    return 0


def cmd_upsert(args: argparse.Namespace) -> int:
    client = build_client()
    if args.file:
        content = Path(args.file).read_text()
    else:
        content = sys.stdin.read()
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
        emit(result.to_dict(), as_json=True)
    else:
        result_payload = result.to_dict()
        response = result_payload.get("responseResult", {})
        details = []
        metadata = result.metadata or {}
        if metadata.get("description_preserved"):
            details.append("description preserved")
        if metadata.get("tags_preserved"):
            details.append("tags preserved")
        suffix = f" [{', '.join(details)}]" if details else ""
        print(f"{result.action}: {args.path} ({response.get('message', 'ok')}){suffix}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    client = build_client()
    result = client.delete_page_by_path(args.path)
    if args.json:
        emit(result.to_dict(), as_json=True)
    else:
        response = result.to_dict().get("responseResult", {})
        print(f"deleted: {args.path} ({response.get('message', 'ok')})")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    client = build_client()
    result = client.move_page(source_path=args.source_path, destination_path=args.destination_path, title=args.title)
    if args.json:
        emit(result.to_dict(), as_json=True)
    else:
        response = result.to_dict().get("responseResult", {})
        print(f"moved: {args.source_path} -> {args.destination_path} ({response.get('message', 'ok')})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wikijs-tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--prefix")
    p_list.add_argument("--query", help="case-insensitive substring filter across path, title, and description")
    p_list.add_argument("--regex", help="regular expression filter across path, title, and description")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get")
    p_get.add_argument("path")
    p_get.add_argument("--json", action="store_true")
    p_get.set_defaults(func=cmd_get)

    p_upsert = sub.add_parser("upsert")
    p_upsert.add_argument("path")
    p_upsert.add_argument("title")
    p_upsert.add_argument("--file")
    p_upsert.add_argument("--description")
    p_upsert.add_argument("--tags", nargs="*")
    p_upsert.add_argument("--replace-description", action="store_true", help="replace existing description instead of preserving it when omitted")
    p_upsert.add_argument("--replace-tags", action="store_true", help="replace existing tags instead of preserving them when omitted")
    p_upsert.add_argument("--json", action="store_true")
    p_upsert.set_defaults(func=cmd_upsert)

    p_delete = sub.add_parser("delete")
    p_delete.add_argument("path")
    p_delete.add_argument("--json", action="store_true")
    p_delete.set_defaults(func=cmd_delete)

    p_move = sub.add_parser("move")
    p_move.add_argument("source_path")
    p_move.add_argument("destination_path")
    p_move.add_argument("--title", help="optional new title; defaults to the existing title")
    p_move.add_argument("--json", action="store_true")
    p_move.set_defaults(func=cmd_move)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WikiJsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
