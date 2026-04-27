from __future__ import annotations

import json

from wikijs_client import cli
from wikijs_client import client as client_module
from wikijs_client.client import WikiJsAmbiguousMatchError, WikiJsError, WikiJsNotFoundError, WikiJsValidationError
from wikijs_client.models import MutationResult, PageDetail, PageSummary, SiteVersion


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self):
        self.deleted = []
        self.moved = []

    def get_version(self, *, target_version=""):
        return SiteVersion(
            current_version="2.5.312",
            latest_version="2.5.312",
            latest_version_release_date="2026-02-11T00:00:00.000Z",
            upgrade_capable=False,
            target_version=target_version,
            matches_target=None if not target_version else target_version == "2.5.312",
        )

    def list_pages(self, *, query="", path=""):
        if query == "alpha":
            return [PageSummary(id=1, path="ideas/a", title="A", description="alpha note")]
        if path == "ideas":
            return [PageSummary(id=1, path="ideas/a", title="A", description="alpha note")]
        return [
            PageSummary(id=1, path="ideas/a", title="A", description="alpha note"),
            PageSummary(id=2, path="infra/b", title="B", description="beta infra"),
        ]

    def search_pages(self, *, query, path=""):
        if query == "alpha" and path == "":
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
            target={"path": kwargs["path"], "title": kwargs["title"]},
            changed={"created": True, "updated": False, "deleted": False},
            metadata={
                "description_preserved": kwargs.get("preserve_description"),
                "tags_preserved": kwargs.get("preserve_tags"),
            },
        )

    def delete_page_by_path(self, path):
        self.deleted.append(path)
        return MutationResult(
            action="deleted",
            succeeded=True,
            message="deleted",
            page={"id": 9, "path": path, "title": "Deleted"},
            target={"path": path},
            resolved_page={"id": 9, "path": path, "title": "Deleted"},
            changed={"created": False, "updated": False, "deleted": True},
        )

    def move_page(self, *, source_path, destination_path, title=None):
        self.moved.append((source_path, destination_path, title))
        return MutationResult(
            action="moved",
            succeeded=True,
            message="Page has been updated.",
            page={"path": destination_path, "title": title or "A"},
            target={"source_path": source_path, "destination_path": destination_path, "title": title or "A"},
            resolved_page={"id": 1, "path": source_path, "title": "A"},
            changed={"created": False, "updated": True, "deleted": False, "path": True, "title": bool(title)},
        )


def test_run_versioncheck_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.run_versioncheck(as_json=True, debug=False) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["currentVersion"] == "2.5.312"
    assert out["targetVersion"] == "2.5.312"
    assert out["matchesTarget"] is True


def test_run_versioncheck_warns_on_mismatch(monkeypatch, capsys):
    class MismatchClient(DummyClient):
        def get_version(self, *, target_version=""):
            return SiteVersion(
                current_version="2.5.999",
                latest_version="2.5.999",
                latest_version_release_date="2026-02-11T00:00:00.000Z",
                upgrade_capable=False,
                target_version=target_version,
                matches_target=False,
            )

    monkeypatch.setattr(cli, "build_client", lambda **kwargs: MismatchClient())
    assert cli.run_versioncheck(as_json=False, debug=False) == 0
    out = capsys.readouterr().out
    assert "warning: expected 2.5.312, got 2.5.999" in out


def test_cmd_list_no_args_shows_all(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(query=None, path=None, regex=None, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" in out
    assert "ID" in out


def test_cmd_list_uses_server_query(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(query="alpha", path=None, regex=None, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out


def test_cmd_list_uses_server_path(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(query=None, path="ideas", regex=None, json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out


def test_cmd_list_filters_regex(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(query=None, path=None, regex=r"ideas/.*", json=False)
    assert cli.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "ideas/a" in out
    assert "infra/b" not in out


def test_cmd_search_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(text="alpha", json=True)
    assert cli.cmd_search(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["path"] == "ideas/a"


def test_cmd_exists_json_found(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(path="ideas/a", json=True)
    assert cli.cmd_exists(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "ideas/a"
    assert out["exists"] is True


def test_cmd_exists_json_missing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(path="ideas/missing", json=True)
    assert cli.cmd_exists(args) == cli.EXIT_NOT_FOUND
    out = json.loads(capsys.readouterr().out)
    assert out["exists"] is False


def test_cmd_get_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(path="ideas/a", json=True)
    assert cli.cmd_get(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "ideas/a"


def test_cmd_upsert_reads_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=False, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "created"
    assert out["page"]["path"] == "ideas/test"
    assert out["target"]["path"] == "ideas/test"


def test_cmd_upsert_dry_run_create_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=True, diff=False, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "create"
    assert out["dry_run"] is True
    assert out["target"]["path"] == "ideas/test"
    assert out["target"]["title"] == "Test"
    assert out["changed"]["created"] is True
    assert out["changed"]["updated"] is False
    assert out["metadata"]["content_source"] == "file"
    assert out["metadata"]["change_summary"]["content"]["changed"] is True
    assert out["metadata"]["change_summary"]["content"]["oldChars"] == 0
    assert out["metadata"]["change_summary"]["content"]["newChars"] == len("# Body\n")
    assert "resolvedPage" not in out


def test_cmd_upsert_dry_run_update_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/a", title="A", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=True, diff=False, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "update"
    assert out["dry_run"] is True
    assert out["resolvedPage"]["id"] == 1
    assert out["resolvedPage"]["path"] == "ideas/a"
    assert out["metadata"]["description_preserved"] is True
    assert out["metadata"]["tags_preserved"] is True
    assert out["changed"]["updated"] is True
    assert out["changed"]["deleted"] is False
    assert out["metadata"]["change_summary"]["content"]["changed"] is True
    assert out["metadata"]["change_summary"]["content"]["oldChars"] == len("hello")
    assert out["metadata"]["change_summary"]["content"]["newChars"] == len("# Body\n")
    assert out["metadata"]["change_summary"]["title"]["changed"] is False


def test_cmd_upsert_dry_run_diff_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/a", title="A", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=True, diff=True, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["diff"][0] == "--- wiki:ideas/a"
    assert out["diff"][1] == "+++ input:ideas/a"
    assert any(line.startswith("-hello") for line in out["diff"])
    assert any(line.startswith("+# Body") for line in out["diff"])


def test_cmd_delete(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=False, json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["responseResult"]["succeeded"] is True
    assert out["page"]["id"] == 9
    assert out["target"]["path"] == "ideas/test"
    assert out["resolvedPage"]["title"] == "Deleted"
    assert out["changed"]["deleted"] is True
    assert client.deleted == ["ideas/test"]


def test_cmd_delete_dry_run(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=True, json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "delete"
    assert out["dry_run"] is True
    assert out["wouldMutate"] is False
    assert out["target"]["path"] == "ideas/test"
    assert out["changed"]["deleted"] is False
    assert out["metadata"]["found"] is False
    assert client.deleted == []


def test_cmd_delete_dry_run_found_json(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/a", dry_run=True, json=True)
    assert cli.cmd_delete(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "delete"
    assert out["dry_run"] is True
    assert out["wouldMutate"] is True
    assert out["target"]["path"] == "ideas/a"
    assert out["resolvedPage"]["id"] == 1
    assert out["resolvedPage"]["path"] == "ideas/a"
    assert out["changed"]["deleted"] is True
    assert out["metadata"]["found"] is True
    assert client.deleted == []


def test_cmd_upsert_human_output(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=False, json=False)
    assert cli.cmd_upsert(args) == 0
    out = capsys.readouterr().out
    assert "created: ideas/test" in out
    assert "path ideas/test" in out
    assert "title 'Test'" in out
    assert "description preserved" in out
    assert "tags preserved" in out


def test_cmd_upsert_dry_run_human_output(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/a", title="A", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=True, diff=False, json=False)
    assert cli.cmd_upsert(args) == 0
    out = capsys.readouterr().out
    assert "dry-run: would update ideas/a" in out
    assert "id 1" in out
    assert "content changed: 5 -> 7 chars" in out
    assert "title unchanged" in out
    assert "description preserved" in out
    assert "tags preserved" in out


def test_cmd_upsert_dry_run_human_diff_output(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/a", title="A", file=str(p), description=None, tags=None, replace_description=False, replace_tags=False, dry_run=True, diff=True, json=False)
    assert cli.cmd_upsert(args) == 0
    out = capsys.readouterr().out
    assert "--- wiki:ideas/a" in out
    assert "+++ input:ideas/a" in out
    assert "-hello" in out
    assert "+# Body" in out


def test_cmd_move(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title=None, dry_run=False, json=True)
    assert cli.cmd_move(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "moved"
    assert out["target"]["source_path"] == "ideas/a"
    assert out["resolvedPage"]["path"] == "ideas/a"
    assert out["changed"]["path"] is True
    assert out["changed"]["title"] is False
    assert client.moved == [("ideas/a", "ideas/b", None)]


def test_cmd_move_dry_run(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title="B", dry_run=True, json=True)
    assert cli.cmd_move(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "move"
    assert out["dry_run"] is True
    assert out["wouldMutate"] is True
    assert out["target"]["source_path"] == "ideas/a"
    assert out["target"]["destination_path"] == "ideas/b"
    assert out["target"]["title"] == "B"
    assert out["resolvedPage"]["id"] == 1
    assert out["changed"]["updated"] is True
    assert out["changed"]["path"] is True
    assert out["changed"]["title"] is True
    assert out["metadata"]["source_found"] is True
    assert out["metadata"]["destination_exists"] is False
    assert out["metadata"]["destination_conflict"] is False
    assert client.moved == []


def test_cmd_delete_dry_run_human_output_found(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/a", dry_run=True, json=False)
    assert cli.cmd_delete(args) == 0
    out = capsys.readouterr().out
    assert "dry-run: would delete ideas/a" in out
    assert "id 1" in out
    assert "title 'A'" in out


def test_cmd_delete_dry_run_human_output_missing(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=True, json=False)
    assert cli.cmd_delete(args) == 0
    out = capsys.readouterr().out
    assert "dry-run: would not delete ideas/test (page not found)" in out


def test_cmd_move_dry_run_human_output(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title="B", dry_run=True, json=False)
    assert cli.cmd_move(args) == 0
    out = capsys.readouterr().out
    assert "dry-run: would move ideas/a -> ideas/b" in out
    assert "id 1" in out
    assert "title 'A'" in out
    assert "title 'B'" in out


def test_cmd_delete_human_output_includes_identity(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(path="ideas/test", dry_run=False, json=False)
    assert cli.cmd_delete(args) == 0
    out = capsys.readouterr().out
    assert "deleted: ideas/test" in out
    assert "id 9" in out
    assert "title 'Deleted'" in out


def test_cmd_move_human_output_includes_identity(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(source_path="ideas/a", destination_path="ideas/b", title=None, dry_run=False, json=False)
    assert cli.cmd_move(args) == 0
    out = capsys.readouterr().out
    assert "moved: ideas/a -> ideas/b" in out
    assert "path ideas/b" in out
    assert "title 'A'" in out


def test_cmd_move_dry_run_human_output_missing(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    args = cli.argparse.Namespace(source_path="ideas/missing", destination_path="ideas/b", title=None, dry_run=True, json=False)
    assert cli.cmd_move(args) == 0
    out = capsys.readouterr().out
    assert "dry-run: would not move ideas/missing (page not found)" in out


def test_build_parser_includes_new_commands():
    parser = cli.build_parser()
    help_text = parser.format_help()
    list_help = parser._subparsers._group_actions[0].choices["list"].format_help()
    assert "search" in help_text
    assert "exists" in help_text
    assert "upsert" in help_text
    assert "delete" in help_text
    assert "move" in help_text
    assert "--versioncheck" in help_text
    assert "--quiet" in help_text
    assert "--debug" in help_text
    assert "wikijs-client 0.1.2" in help_text
    assert "Use --json to emit structured output." in help_text
    assert "Use '<command> --help' for command-specific arguments and examples." in help_text
    assert "--query" in list_help
    assert "--path" in list_help
    assert "--json" not in list_help
    upsert_help = parser._subparsers._group_actions[0].choices["upsert"].format_help()
    assert "--dry-run" in upsert_help
    assert "--diff" in upsert_help
    assert "include a unified diff" in upsert_help


def test_main_reports_wikijs_error(monkeypatch, capsys):
    def fake_build_client(**kwargs):
        raise WikiJsError("bad graphql")

    monkeypatch.setattr(cli, "build_client", fake_build_client)
    assert cli.main(["list"]) == 1
    err = capsys.readouterr().err
    assert "Error: bad graphql" in err


def test_main_reports_missing_env(capsys, monkeypatch):
    monkeypatch.delenv("WIKIJS_URL", raising=False)
    monkeypatch.delenv("WIKIJS_TOKEN", raising=False)
    assert cli.main(["list"]) == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "WIKIJS_URL and WIKIJS_TOKEN must be set" in err


def test_cmd_get_missing_returns_not_found(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    args = cli.argparse.Namespace(path="ideas/missing", json=False)
    assert cli.cmd_get(args) == cli.EXIT_NOT_FOUND
    err = capsys.readouterr().err
    assert "No page found at path: ideas/missing" in err


def test_main_reports_not_found_with_typed_exit_code(monkeypatch, capsys):
    def fake_build_client(**kwargs):
        class MissingClient(DummyClient):
            def delete_page_by_path(self, path):
                raise WikiJsNotFoundError(f"No page found at path: {path}")

        return MissingClient()

    monkeypatch.setattr(cli, "build_client", fake_build_client)
    assert cli.main(["delete", "ideas/missing"]) == cli.EXIT_NOT_FOUND
    err = capsys.readouterr().err
    assert "No page found at path: ideas/missing" in err


def test_main_reports_ambiguous_with_typed_exit_code(monkeypatch, capsys):
    def fake_build_client(**kwargs):
        class AmbiguousClient(DummyClient):
            def get_page_by_path(self, path):
                raise WikiJsAmbiguousMatchError(f"Multiple pages matched path exactly via pages.search: {path}")

        return AmbiguousClient()

    monkeypatch.setattr(cli, "build_client", fake_build_client)
    assert cli.main(["exists", "ideas/a"]) == cli.EXIT_AMBIGUOUS
    err = capsys.readouterr().err
    assert "Multiple pages matched path exactly" in err


def test_main_reports_validation_with_typed_exit_code(monkeypatch, capsys):
    def fake_build_client(**kwargs):
        raise WikiJsValidationError("bad config")

    monkeypatch.setattr(cli, "build_client", fake_build_client)
    assert cli.main(["list"]) == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "Error: bad config" in err


def test_main_supports_versioncheck_flag(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["--versioncheck", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["targetVersion"] == "2.5.312"


def test_main_supports_quiet_versioncheck(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["--versioncheck", "--quiet"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_quiet_exists_suppresses_success_stdout(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["exists", "ideas/a", "--quiet"]) == cli.EXIT_SUCCESS
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_quiet_get_suppresses_success_stdout(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["get", "ideas/a", "--quiet"]) == cli.EXIT_SUCCESS
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_quiet_delete_suppresses_success_stdout(monkeypatch, capsys):
    client = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: client)
    assert cli.main(["delete", "ideas/test", "--quiet"]) == cli.EXIT_SUCCESS
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert client.deleted == ["ideas/test"]


def test_quiet_preserves_stderr_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["get", "ideas/missing", "--quiet"]) == cli.EXIT_NOT_FOUND
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "No page found at path: ideas/missing" in captured.err


def test_quiet_and_json_are_mutually_exclusive(capsys):
    try:
        cli.main(["exists", "ideas/a", "--quiet", "--json"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected parser to exit")
    captured = capsys.readouterr()
    assert "--quiet and --json cannot be used together" in captured.err


def test_quiet_flag_works_before_subcommand_too(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    assert cli.main(["--quiet", "exists", "ideas/a"]) == cli.EXIT_SUCCESS
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_debug_output_goes_to_stderr_and_json_stdout_stays_parseable(monkeypatch, capsys):
    monkeypatch.setenv("WIKIJS_URL", "https://example.invalid/graphql?token=leakme")
    monkeypatch.setenv("WIKIJS_TOKEN", "super-secret-token")

    def fake_post(url, json=None, headers=None, timeout=None):
        query = (json or {}).get("query", "")
        variables = (json or {}).get("variables", {})
        if "search(path:" in query:
            return FakeResponse({"data": {"pages": {"search": {"results": [{"id": 7, "path": variables["path"], "title": "Example"}]}}}})
        if "single(id:" in query:
            return FakeResponse({"data": {"pages": {"single": {"id": 7, "path": "ideas/a", "title": "Example", "content": "body", "description": "", "tags": []}}}})
        raise AssertionError(query)

    monkeypatch.setattr(client_module.requests, "post", fake_post)
    assert cli.main(["exists", "ideas/a", "--json", "--debug"]) == cli.EXIT_SUCCESS
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out == {"path": "ideas/a", "exists": True}
    assert "debug: command=exists" in captured.err
    assert "debug: client config: url=https://example.invalid/graphql locale=en" in captured.err
    assert "debug: graphql request: pages.search" in captured.err
    assert "debug: graphql request: pages.single" in captured.err
    assert "super-secret-token" not in captured.err
    assert "leakme" not in captured.err


def test_debug_flag_works_before_subcommand_too(monkeypatch, capsys):
    monkeypatch.setenv("WIKIJS_URL", "https://example.invalid/graphql")
    monkeypatch.setenv("WIKIJS_TOKEN", "secret")

    def fake_post(url, json=None, headers=None, timeout=None):
        query = (json or {}).get("query", "")
        if "search(path:" in query:
            return FakeResponse({"data": {"pages": {"search": {"results": []}}}})
        if "list(orderBy: PATH)" in query:
            return FakeResponse({"data": {"pages": {"list": []}}})
        raise AssertionError(query)

    monkeypatch.setattr(client_module.requests, "post", fake_post)
    assert cli.main(["--debug", "exists", "ideas/missing", "--json"]) == cli.EXIT_NOT_FOUND
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out == {"path": "ideas/missing", "exists": False}
    assert "debug: command=exists" in captured.err


def test_build_client_uses_optional_locale(monkeypatch):
    monkeypatch.setenv("WIKIJS_URL", "https://example.invalid/graphql")
    monkeypatch.setenv("WIKIJS_TOKEN", "secret")
    monkeypatch.setenv("WIKIJS_LOCALE", "fr")
    client = cli.build_client()
    assert client.url == "https://example.invalid/graphql"
    assert client.token == "secret"
    assert client.locale == "fr"


def test_cmd_upsert_replace_flags_flow(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_client", lambda **kwargs: DummyClient())
    p = tmp_path / "body.md"
    p.write_text("# Body\n")
    args = cli.argparse.Namespace(path="ideas/test", title="Test", file=str(p), description="desc", tags=["a"], replace_description=True, replace_tags=True, dry_run=False, json=True)
    assert cli.cmd_upsert(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["metadata"]["description_preserved"] is False
    assert out["metadata"]["tags_preserved"] is False
