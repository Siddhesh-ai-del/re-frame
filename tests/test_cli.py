"""CLI tests for ``reframe.cli`` — argument validation, key policy, the serve seam.

``main`` is exercised end-to-end minus the network: ``create_service`` and the
``_run_uvicorn`` seam are monkeypatched, so no server thread is ever started
and no LLM call is ever made. The key policy follows the actual
``reframe.config`` behavior: development allows no key (the server still
starts with a fail-closed generator — generated turns map to 503 while
crisis/scripted routes keep working), while a rejected configuration (e.g.
``production`` without ``REFRAME_API_KEY``) exits 2 without serving.

The module entry guard (``python -m reframe.cli``) is covered by re-executing
the module under ``run_name="__main__"`` with a stubbed ``uvicorn`` in
``sys.modules`` — this also proves the lazy ``import uvicorn`` inside
``_run_uvicorn`` is the only place server machinery is pulled in.
"""

import runpy
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import reframe.api.service as service_module
import reframe.cli as cli
from reframe.api.app import CHAT_UNAVAILABLE_DETAIL
from reframe.generation import ConstrainedGenerator
from reframe.pipeline.messages import CRISIS_RESPONSE

TEST_API_KEY = "sk-test-dummy"


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every REFRAME_* variable so the config behavior is deterministic."""
    monkeypatch.delenv("REFRAME_ENV", raising=False)
    monkeypatch.delenv("REFRAME_API_KEY", raising=False)


def _record_service(monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict[str, object]], object]:
    """Replace ``cli.create_service`` with a recorder returning a sentinel app."""
    sentinel_app = object()
    calls: list[dict[str, object]] = []

    def _fake_create_service(**kwargs: object) -> object:
        calls.append(kwargs)
        return sentinel_app

    monkeypatch.setattr(cli, "create_service", _fake_create_service)
    return calls, sentinel_app


def _record_serve(monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, dict[str, object]]]:
    """Replace ``cli._run_uvicorn`` with a recorder; no server is ever started."""
    calls: list[tuple[object, dict[str, object]]] = []

    def _fake_run_uvicorn(app: object, *, host: str, port: int, log_level: str) -> None:
        calls.append((app, {"host": host, "port": port, "log_level": log_level}))

    monkeypatch.setattr(cli, "_run_uvicorn", _fake_run_uvicorn)
    return calls


# ---------------------------------------------------------------------------
# Argument parsing: defaults and pass-through
# ---------------------------------------------------------------------------


def test_defaults_used_when_no_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    monkeypatch.setenv("REFRAME_API_KEY", TEST_API_KEY)
    service_calls, sentinel_app = _record_service(monkeypatch)
    serve_calls = _record_serve(monkeypatch)

    exit_code = cli.main([])

    assert exit_code == 0
    assert len(service_calls) == 1
    assert isinstance(service_calls[0]["generator"], ConstrainedGenerator)
    assert service_calls[0]["db_path"] == "reframe.db"
    assert serve_calls == [(sentinel_app, {"host": "127.0.0.1", "port": 8000, "log_level": "info"})]


def test_cli_options_pass_through(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clean_env(monkeypatch)
    monkeypatch.setenv("REFRAME_API_KEY", TEST_API_KEY)
    service_calls, sentinel_app = _record_service(monkeypatch)
    serve_calls = _record_serve(monkeypatch)
    db_path = tmp_path / "x.db"

    exit_code = cli.main(
        [
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--db",
            str(db_path),
            "--log-level",
            "warning",
        ]
    )

    assert exit_code == 0
    assert service_calls[0]["db_path"] == str(db_path)
    assert serve_calls == [
        (sentinel_app, {"host": "0.0.0.0", "port": 9000, "log_level": "warning"})
    ]


# ---------------------------------------------------------------------------
# Argument validation: out-of-range ports are argparse errors (exit 2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("port", [0, 70000])
def test_out_of_range_port_is_an_argparse_error(
    port: int, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_env(monkeypatch)
    service_calls, _sentinel_app = _record_service(monkeypatch)
    serve_calls = _record_serve(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--port", str(port)])

    assert excinfo.value.code == 2
    assert "port" in capsys.readouterr().err
    assert service_calls == []
    assert serve_calls == []


# ---------------------------------------------------------------------------
# Key policy (matches reframe.config behavior)
# ---------------------------------------------------------------------------


def test_configured_api_key_builds_the_real_generator(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_env(monkeypatch)
    monkeypatch.setenv("REFRAME_API_KEY", TEST_API_KEY)
    service_calls, _sentinel_app = _record_service(monkeypatch)
    serve_calls = _record_serve(monkeypatch)

    exit_code = cli.main([])

    assert exit_code == 0
    generator = service_calls[0]["generator"]
    assert type(generator) is ConstrainedGenerator
    assert "no LLM API key" not in capsys.readouterr().err
    assert len(serve_calls) == 1


def test_missing_api_key_serves_with_a_fail_closed_generator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_env(monkeypatch)
    db_path = tmp_path / "cli.db"
    service_calls: list[dict[str, object]] = []
    apps: list[object] = []

    def _real_service(**kwargs: object) -> object:
        service_calls.append(kwargs)
        app = service_module.create_service(**kwargs)
        apps.append(app)
        return app

    monkeypatch.setattr(cli, "create_service", _real_service)
    serve_calls = _record_serve(monkeypatch)

    exit_code = cli.main(["--db", str(db_path)])

    assert exit_code == 0
    assert "no LLM API key configured" in capsys.readouterr().err
    assert isinstance(service_calls[0]["generator"], cli._UnconfiguredGenerator)
    assert service_calls[0]["db_path"] == str(db_path)
    # Config allows development without a key, so the server still starts.
    assert len(serve_calls) == 1

    with TestClient(apps[0]) as client:
        generated = client.post("/chat", json={"message": "I can't stop thinking about work"})
        assert generated.status_code == 503
        assert generated.json()["detail"] == CHAT_UNAVAILABLE_DETAIL
        assert "api key" not in generated.text.lower()

        # Scripted routes never call the generator, so they keep working.
        crisis = client.post("/chat", json={"message": "I want to kill myself"})
        assert crisis.status_code == 200
        crisis_body = crisis.json()
        assert crisis_body["route"] == "crisis_bypass"
        assert crisis_body["reply"] == CRISIS_RESPONSE.text
        assert len(crisis_body["resources"]) >= 1


def test_rejected_settings_exit_2_without_starting_the_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_env(monkeypatch)
    # Production without a key is the config module's fail-closed boundary.
    monkeypatch.setenv("REFRAME_ENV", "production")
    service_calls, _sentinel_app = _record_service(monkeypatch)
    serve_calls = _record_serve(monkeypatch)

    exit_code = cli.main([])

    assert exit_code == 2
    assert "REFRAME_API_KEY" in capsys.readouterr().err
    assert service_calls == []
    assert serve_calls == []


# ---------------------------------------------------------------------------
# Module entry: ``python -m reframe.cli`` and the lazy uvicorn import
# ---------------------------------------------------------------------------


def test_module_entry_guard_raises_system_exit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    monkeypatch.setenv("REFRAME_API_KEY", TEST_API_KEY)
    monkeypatch.setattr(sys, "argv", ["reframe"])
    # Drop the already-imported module so runpy executes it exactly as a fresh
    # `python -m reframe.cli` process would (monkeypatch restores it).
    monkeypatch.delitem(sys.modules, "reframe.cli")
    sentinel_app = object()
    service_calls: list[dict[str, object]] = []

    def _fake_create_service(**kwargs: object) -> object:
        service_calls.append(kwargs)
        return sentinel_app

    monkeypatch.setattr(service_module, "create_service", _fake_create_service)
    serve_calls: list[tuple[object, dict[str, object]]] = []

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        serve_calls.append((app, kwargs))

    stub_uvicorn = types.ModuleType("uvicorn")
    stub_uvicorn.run = _fake_uvicorn_run
    monkeypatch.setitem(sys.modules, "uvicorn", stub_uvicorn)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("reframe.cli", run_name="__main__")

    assert excinfo.value.code == 0
    assert service_calls and service_calls[0]["db_path"] == "reframe.db"
    assert serve_calls == [(sentinel_app, {"host": "127.0.0.1", "port": 8000, "log_level": "info"})]


def test_importing_the_cli_module_does_not_import_uvicorn() -> None:
    # reframe.cli was imported at collection time; server machinery must not
    # have come with it (uvicorn is imported lazily inside _run_uvicorn).
    assert "reframe.cli" in sys.modules
    assert "uvicorn" not in sys.modules
