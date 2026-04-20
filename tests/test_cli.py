from __future__ import annotations

import json

from wikijs_graphql_tool import cli
from wikijs_graphql_tool.client import WikiJsError


class DummyClient:
    def __init__(self):
        self.deleted = []

    def list_pages(self):
        return [
            {"id": 1, "path": "ideas/a", "title": "A"},
            {"id": 2, "path": "infra/b", "title": "B"},
        ]

    def get_page_by_path(self, path):
        if path == "ideas/a":
            return {"id": 1, "path": path, "title": "A", "content": "hello"}
        return None

    def upsert_page(self, **kwargs):
        return {"action": "created", "responseResult": {"succeeded": True}, "page": {"path": kwargs["path"], "title": kwargs["title"]}}

    def delete_page_by_path(self, path):
        self.deleted.append(path)
        return {"responseResult": {"succeeded": True, "message": "deleted"}}


def test_cmd_list_filters_prefix(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    args = cli.argparse.Namespace(prefix="ideas", json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out


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
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description="", tags=[], json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "created"


def test_cmd_delete(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda: client)
    args = cli.argparse.Namespace(path="ideas/test", json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["responseResult"]["succeeded"] is True
    assert client.deleted == ["ideas/test"]


def test_cmd_upsert_human_output(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description="", tags=[], json=False)
    assert cli.cmd_upsert(args) == 0
    out = capsys.readouterr().out
    assert "created: ideas/test" in out


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
