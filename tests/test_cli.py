from __future__ import annotations

import json

from wikijs_client import cli
from wikijs_client.client import WikiJsError
from wikijs_client.models import MutationResult, PageDetail, PageSummary


class DummyClient:
    def __init__(self):
        self.deleted = []
        self.moved = []

    def list_pages(self):
        return [
            PageSummary(id=1, path="ideas/a", title="A", description="alpha note"),
            PageSummary(id=2, path="infra/b", title="B", description="beta infra"),
        ]

    def search_pages(self, *, query, path=""):
        assert path == ""
        if query == "alpha":
            return [PageSummary(id=1, path="ideas/a", title="A", description="alpha note")]
        return []

    def get_page_by_path(self, path):
        if path == "ideas/a":
            return PageDetail(id=1, path=path, title="A", content="hello", description="", tags=[])
        return None

    def upsert_page(self, **kwargs):
        return MutationResult(
            action="created",
            succeeded=True,
            message="Page created successfully.",
            page={"path": kwargs["path"], "title": kwargs["title"]},
            changed={"created": True, "updated": False, "deleted": False},
            metadata={
                "description_preserved": kwargs.get("preserve_description"),
                "tags_preserved": kwargs.get("preserve_tags"),
            },
        )

    def delete_page_by_path(self, path):
        self.deleted.append(path)
        return MutationResult(action="deleted", succeeded=True, message="deleted", changed={"created": False, "updated": False, "deleted": True})

    def move_page(self, *, source_path, destination_path, title=None):
        self.moved.append((source_path, destination_path, title))
        return MutationResult(
            action="moved",
            succeeded=True,
            message="Page has been updated.",
            page={"path": destination_path, "title": title or "A"},
            changed={"created": False, "updated": True, "deleted": False, "path": True, "title": bool(title)},
        )


def test_cmd_list_filters_prefix(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(prefix="ideas", query=None, regex=None, limit=None, offset=0, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out
    assert "ID" in out


def test_cmd_list_filters_query(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(prefix=None, query="beta", regex=None, limit=None, offset=0, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "infra/b" in out
    assert "ideas/a" not in out


def test_cmd_list_filters_regex(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(prefix=None, query=None, regex=r"ideas/.*", limit=None, offset=0, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out


def test_cmd_list_json_includes_pagination(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(prefix=None, query=None, regex=None, limit=1, offset=1, json=True)
    assert cli.cmd_list(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["pagination"] == {"offset": 1, "limit": 1, "returned": 1, "total": 2}
    assert len(out["pages"]) == 1
    assert out["pages"][0]["path"] == "infra/b"


def test_cmd_search_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(text="alpha", json=True)
    assert cli.cmd_search(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["path"] == "ideas/a"


def test_cmd_exists_json_found(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(path="ideas/a", json=True)
    assert cli.cmd_exists(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "ideas/a"
    assert out["exists"] is True


def test_cmd_exists_json_missing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(path="ideas/missing", json=True)
    assert cli.cmd_exists(args) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["exists"] is False


def test_cmd_get_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(path="ideas/a", json=True)
    assert cli.cmd_get(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "ideas/a"


def test_cmd_upsert_reads_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "created"


def test_cmd_delete(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=False, json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["responseResult"]["succeeded"] is True
    assert out["changed"]["deleted"] is True
    assert client.deleted == ["ideas/test"]


def test_cmd_delete_dry_run(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=True, json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "delete"
    assert out["dry_run"] is True
    assert client.deleted == []


def test_cmd_upsert_human_output(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, json=False)
    assert cli.cmd_upsert(args) == 0
    out = capsys.readouterr().out
    assert "created: ideas/test" in out
    assert "description preserved" in out
    assert "tags preserved" in out


def test_cmd_move(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title=None, dry_run=False, json=True)
    assert cli.cmd_move(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "moved"
    assert out["changed"]["path"] is True
    assert out["changed"]["title"] is False
    assert client.moved == [("ideas/a", "ideas/b", None)]


def test_cmd_move_dry_run(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title="B", dry_run=True, json=True)
    assert cli.cmd_move(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "move"
    assert out["dry_run"] is True
    assert out["title"] == "B"
    assert client.moved == []


def test_build_parser_includes_new_commands():
    parser = cli.build_parser()
    help_text = parser.format_help()
    list_help = parser._subparsers._group_actions[0].choices["list"].format_help()
    assert "search" in help_text
    assert "exists" in help_text
    assert "--limit" in list_help
    assert "--offset" in list_help


def test_main_reports_wikijs_error(monkeypatch, capsys):
    def fake_build_client():
        raise WikiJsError("bad graphql")

    monkeypatch.setattr(cli, "build_client", fake_build_client)
    assert cli.main(["list"]) == 1
    err = capsys.readouterr().err
    assert "Error: bad graphql" in err


def test_main_reports_missing_env(capsys, monkeypatch):
    monkeypatch.delenv("WIKIJS_URL", raising=False)
    monkeypatch.delenv("WIKIJS_TOKEN", raising=False)
    assert cli.main(["list"]) != 0
    err = capsys.readouterr().err
    assert "WIKIJS_URL and WIKIJS_TOKEN must be set" in err


def test_build_client_uses_optional_locale(monkeypatch):
    monkeypatch.setenv("WIKIJS_URL", "https://example.invalid/graphql")
    monkeypatch.setenv("WIKIJS_TOKEN", "secret")
    monkeypatch.setenv("WIKIJS_LOCALE", "fr")
    monkeypatch.setenv("WIKIJS_EXACT_PATH_LOOKUP", "list")
    client = cli.build_client()
    assert client.url == "https://example.invalid/graphql"
    assert client.token == "secret"
    assert client.locale == "fr"
    assert client.exact_path_lookup_mode == "list"


def test_cmd_upsert_replace_flags_flow(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description="desc", tags=["a"], replace_description=True, replace_tags=True, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["metadata"]["description_preserved"] is False
    assert out["metadata"]["tags_preserved"] is False
