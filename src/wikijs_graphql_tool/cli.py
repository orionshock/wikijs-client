from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .client import WikiJsClient, WikiJsError


def build_client() -> WikiJsClient:
    url = os.environ.get("WIKIJS_URL")
    token = os.environ.get("WIKIJS_TOKEN")
    if not url or not token:
        raise SystemExit("WIKIJS_URL and WIKIJS_TOKEN must be set")
    return WikiJsClient(url=url, token=token)


def cmd_list(args: argparse.Namespace) -> int:
    client = build_client()
    pages = client.list_pages()
    if args.prefix:
        pages = [p for p in pages if p["path"].startswith(args.prefix)]
    if args.json:
        print(json.dumps(pages, indent=2))
    else:
        for page in pages:
            print(f'{page["id"]}\t{page["path"]}\t{page["title"]}')
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    client = build_client()
    page = client.get_page_by_path(args.path)
    if not page:
        print(f"No page found at path: {args.path}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(page, indent=2))
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
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    client = build_client()
    result = client.delete_page_by_path(args.path)
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
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
    p_upsert.add_argument("--description", default="")
    p_upsert.add_argument("--tags", nargs="*", default=[])
    p_upsert.set_defaults(func=cmd_upsert)

    p_delete = sub.add_parser("delete")
    p_delete.add_argument("path")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    try:
        return args.func(args)
    except WikiJsError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
