"""Keep runtime modules independent from historical root experiment scripts."""
import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_root_has_only_service_entry_points():
    assert {p.name for p in ROOT.glob("*.py")} == {
        "run_server.py", "run_accepted_server.py"}


def test_no_imports_of_root_experiment_modules():
    for path in (ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            assert not any(n.startswith(("run_", "render_")) for n in names), path


@pytest.mark.parametrize("module", ["expression_depth", "multiview_nasal", "projective_texture"])
def test_stage_resource_root_is_repository_root(module):
    loaded = importlib.import_module("src.pipeline.stages." + module)
    assert loaded.ROOT == ROOT


def test_roma_worker_path_still_resolves():
    from src.pipeline.stages.cross_view_observations import DEFAULT_ROMA_WORKER
    assert DEFAULT_ROMA_WORKER == ROOT / "src/geometry/roma_nasal_worker.py"
    assert DEFAULT_ROMA_WORKER.is_file()


def test_projective_stage_dispatches_package_module(tmp_path, monkeypatch):
    from src.pipeline import accepted_stages
    from src import config as cfg
    monkeypatch.setattr(cfg, "CAMERA_CALIBRATION_PATH", tmp_path / "original.json")
    calls = []
    monkeypatch.setattr(accepted_stages.runpy, "run_module",
                        lambda name, **kwargs: calls.append((name, kwargs)))
    monkeypatch.setattr(accepted_stages.sys, "argv", [])
    accepted_stages.run_stage("projective", tmp_path, tmp_path / "later.json")
    assert calls == [("src.pipeline.stages.projective_texture", {"run_name": "__main__"})]
