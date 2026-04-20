from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .client import WikiJsClient, WikiJsError


def build_client() -> WikiJsClient:
    url = os.environ.get("WIKIJS_URL")
    token = os.environ.get("WIKIJS_TOKEN")
    if not url or not token:
        raise WikiJsError("WIKIJS_URL and WIKIJS_TOKEN must be set")
    return WikiJsClient(url=url, token=token)


def emit(data: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))


def cmd_list(args: argparse.Namespace) -> int:
    client = build_client()
    pages = client.list_pages()
    if args.prefix:
        pages = [p for p in pages if p["path"].startswith(args.prefix)]
    if args.json:
        emit(pages, as_json=True)
    else:
        for page in pages:
            description = page.get("description") or ""
            print(f'{page["id"]}\t{page["path"]}\t{page["title"]}\t{description}')
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    client = build_client()
    page = client.get_page_by_path(args.path)
    if not page:
        print(f"No page found at path: {args.path}", file=sys.stderr)
        return 1
    if args.json:
        emit(page, as_json=True)
    else:
        print(page["content"])
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
        emit(result, as_json=True)
    else:
        response = result.get("responseResult", {})
        print(f"{result['action']}: {args.path} ({response.get('message', 'ok')})")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    client = build_client()
    result = client.delete_page_by_path(args.path)
    if args.json:
        emit(result, as_json=True)
    else:
        response = result.get("responseResult", {})
        print(f"deleted: {args.path} ({response.get('message', 'ok')})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wikijs-tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--prefix")
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
