"""Contract tests; expensive reconstruction is replaced at the process boundary."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.pipeline.accepted_capture import capture_images


def captures(tmp_path):
    folder = tmp_path / "capture"
    folder.mkdir()
    for camera in ("camera1", "camera2", "camera3"):
        (folder / f"{camera}_test.jpg").write_bytes(camera.encode())
    return folder


def test_camera_mapping(tmp_path):
    images = capture_images(captures(tmp_path), allowed_root=tmp_path)
    assert images["left"].name.startswith("camera1_")
    assert images["right"].name.startswith("camera3_")


def test_duplicate_input_rejected(tmp_path):
    folder = captures(tmp_path)
    (folder / "camera1_duplicate.jpg").touch()
    with pytest.raises(ValueError, match="exactly one"):
        capture_images(folder)


def test_outside_root_rejected(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        capture_images(captures(tmp_path), allowed_root=tmp_path / "other")


@pytest.mark.parametrize("failed_stage", [None, "roma", "baseline"])
def test_pipeline_order_and_failure(tmp_path, monkeypatch, failed_stage):
    from src import config as cfg
    from src.pipeline import accepted
    from src.pipeline.accepted_capture import sha256
    folder = captures(tmp_path)
    images = capture_images(folder)
    calibration = tmp_path / "calibration.json"
    calibration.write_text("{}")
    baseline_calibration = tmp_path / "baseline_calibration.json"
    baseline_calibration.write_text('{"role": "baseline"}')
    monkeypatch.setattr(cfg, "CAMERA_CALIBRATION_PATH", calibration)
    contract = {"images": {k: {"sha256": sha256(v)} for k, v in images.items()},
                "calibration_sha256": sha256(calibration),
                "baseline_calibration": str(baseline_calibration),
                "baseline_calibration_sha256": sha256(baseline_calibration)}
    monkeypatch.setattr(accepted, "preflight", lambda *a: contract)
    executed = []
    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(stdout="c481186", returncode=0)
        stage = command[4]
        root = Path(command[5])
        executed.append(stage)
        if stage == failed_stage:
            kwargs["stdout"].write("test failure")
            return SimpleNamespace(returncode=1)
        if stage == "biharmonic":
            model = root / "stages/biharmonic/meshes/face.glb"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"model" * 100)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(accepted.subprocess, "run", run)
    params = dict(session_id=1, patient_id="test", image_paths=images, session_output_dir=tmp_path / "run")
    if failed_stage:
        with pytest.raises(RuntimeError, match=failed_stage):
            accepted.run_accepted_pipeline(**params)
        assert executed[-1] == failed_stage
    else:
        assert accepted.run_accepted_pipeline(**params).is_file()
        assert executed == list(accepted.STAGES)
        with pytest.raises(FileExistsError):
            accepted.run_accepted_pipeline(**params)
    manifest = json.loads((tmp_path / "run/accepted_c481186/run_manifest.json").read_text())
    assert manifest["status"] == ("error" if failed_stage else "done")
    assert manifest["historical_model_reused"] is False
    inputs = tmp_path / "run/accepted_c481186/inputs"
    assert sha256(inputs / "baseline_calibration.json") == sha256(baseline_calibration)
    assert sha256(inputs / "calibration.json") == sha256(calibration)


@pytest.mark.parametrize("expression_source", ["initializer", "zero"])
def test_baseline_uses_original_intrinsics_without_rig_pose(tmp_path, monkeypatch, expression_source):
    import sys
    from src import config as cfg
    from src.pipeline import accepted_stages

    images = {"left": Path("camera1.jpg"), "front": Path("camera2.jpg"), "right": Path("camera3.jpg")}
    monkeypatch.setattr(accepted_stages, "capture_images", lambda _: images)
    monkeypatch.setattr(cfg, "CAMERA_CALIBRATION_PATH", tmp_path / "later.json")
    monkeypatch.setattr(cfg, "STABLE_USE_CALIBRATED_RIG_EXTRINSICS", True)
    observed = {}
    def baseline(**kwargs):
        observed.update(kwargs)
        assert cfg.CAMERA_CALIBRATION_PATH == tmp_path / "inputs/baseline_calibration.json"
        assert cfg.STABLE_USE_CALIBRATED_RIG_EXTRINSICS is False
        debug = kwargs["session_output_dir"] / "debug"
        debug.mkdir(parents=True)
        for view in images:
            (debug / f"init_view_{view}.json").write_text(json.dumps({"exp_source": expression_source}))
    monkeypatch.setitem(sys.modules, "src.pipeline.stable_three_view",
                        SimpleNamespace(run_stable_three_view_pipeline=baseline))
    if expression_source == "zero":
        with pytest.raises(RuntimeError, match="fallback to zero"):
            accepted_stages.run_stage("baseline", tmp_path, tmp_path / "later.json")
    else:
        accepted_stages.run_stage("baseline", tmp_path, tmp_path / "later.json")
    assert observed["image_paths"] == images


def test_missing_deca_is_rejected_before_reconstruction(tmp_path, monkeypatch):
    from src import config as cfg
    from src.pipeline.accepted import preflight
    missing = tmp_path / "deca_model.tar"
    monkeypatch.setattr(cfg, "DECA_MODEL_PATH", missing)
    with pytest.raises(FileNotFoundError, match="deca_model.tar"):
        preflight({})


@pytest.mark.parametrize("explicit_worker", [False, True])
def test_preflight_uses_portable_worker_path(tmp_path, monkeypatch, explicit_worker):
    import sys
    from src import config as cfg
    from src.pipeline import accepted

    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(cfg, "MODELS_DIR", tmp_path / "models")
    for name in ("DECA_MODEL_PATH", "FLAME_MODEL_PATH", "FLAME_LANDMARK_PATH", "MICA_CHECKPOINT"):
        path = tmp_path / name
        path.write_bytes(b"fixture")
        monkeypatch.setattr(cfg, name, path)
    cache = tmp_path / "models/roma-cache/hub/checkpoints"
    cache.mkdir(parents=True)
    for name in ("roma_outdoor.pth", "dinov2_vitl14_pretrain.pth"):
        (cache / name).write_bytes(b"fixture")
    vendor = tmp_path / "frontend/vendor"
    vendor.mkdir(parents=True)
    (vendor / "three.module.js").write_text("fixture")
    monkeypatch.delenv("FACE3D_ROMA_TORCH_HOME", raising=False)
    monkeypatch.delenv("FACE3D_ROMA_PYTHON", raising=False)
    monkeypatch.setattr(accepted, "validate_images", lambda *args, **kwargs: {
        "calibration": "fixture", "calibration_sha256": "fixture"})
    if explicit_worker:
        missing = tmp_path / "missing-worker-python.exe"
        monkeypatch.setenv("FACE3D_ROMA_PYTHON", str(missing))
        with pytest.raises(FileNotFoundError, match="missing-worker-python"):
            accepted.preflight({})
    else:
        assert Path(sys.executable).is_file()
        assert accepted.preflight({})["baseline_calibration"] == "fixture"


@pytest.mark.parametrize("fail", [False, True])
def test_api_directory_and_completion(tmp_path, monkeypatch, fail):
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from src.api import app as application
    from src.api.db import Base
    from src.pipeline import accepted
    from src import config as cfg

    folder = captures(tmp_path)
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "test.db").as_posix())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async def init():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    async def database():
        async with factory() as session:
            yield session
    monkeypatch.setattr(application, "init_db", init)
    monkeypatch.setattr(application, "SessionLocal", factory)
    monkeypatch.setattr(application, "ROOT", tmp_path)
    monkeypatch.setattr(application, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(cfg, "RECONSTRUCTION_PIPELINE", "accepted_c481186")
    monkeypatch.setenv("FACE3D_CAPTURE_ROOT", str(tmp_path))
    monkeypatch.setattr(accepted, "preflight", lambda *args: {})
    async def job(**kwargs):
        if fail:
            raise RuntimeError("RoMa test failure")
        model = kwargs["session_output_dir"] / "face.glb"
        model.write_bytes(b"test model")
        return model
    monkeypatch.setattr(application, "run_pipeline_async", job)
    application.app.dependency_overrides[application.get_db] = database
    try:
        with TestClient(application.app) as client:
            payload = {"patient_id": "sample", "capture_dir": str(folder)}
            assert client.post("/api/sessions", data=payload,
                               headers={"origin": "http://evil.example"}).status_code == 403
            response = client.post("/api/sessions", data=payload)
            assert response.status_code == 201, response.text
            sid = response.json()["id"]
            detail = client.get(f"/api/sessions/{sid}").json()
            assert detail["status"] == ("error" if fail else "done")
            if fail:
                assert detail["error_msg"] == "RoMa test failure"
                assert client.get(f"/api/sessions/{sid}/model").status_code == 404
            else:
                assert client.get(f"/api/sessions/{sid}/model").content == b"test model"
            assert client.post("/api/sessions", data={"patient_id": "missing"}).status_code == 422
    finally:
        application.app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
