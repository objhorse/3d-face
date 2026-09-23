"""Application orchestration of the c481186 algorithms, without historical inputs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.accepted_capture import CAMERA_BY_VIEW, sha256, validate_images
from src.pipeline.accepted_stages import STAGES

_GPU_LOCK = threading.Lock()
PIPELINE = "accepted_c481186"


def preflight(image_paths: dict[str, Path], manual_intrinsics=None) -> dict:
    from src import config as cfg
    if manual_intrinsics is not None:
        raise ValueError("accepted_c481186 requires the complete rig calibration, not manual intrinsics")
    roma_cache = Path(os.environ.get("FACE3D_ROMA_TORCH_HOME", str(cfg.MODELS_DIR / "roma-cache")))
    required = [cfg.DECA_MODEL_PATH, cfg.FLAME_MODEL_PATH, cfg.FLAME_LANDMARK_PATH, cfg.MICA_CHECKPOINT,
                roma_cache / "hub" / "checkpoints" / "roma_outdoor.pth",
                roma_cache / "hub" / "checkpoints" / "dinov2_vitl14_pretrain.pth",
                cfg.ROOT / "frontend" / "vendor" / "three.module.js",
                Path(os.environ.get("FACE3D_ROMA_PYTHON", sys.executable))]
    for path in required:
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required c481186 dependency missing: {path}")
    contract = validate_images(image_paths, cfg.CAMERA_CALIBRATION_PATH)
    baseline_calibration = Path(os.environ.get("FACE3D_BASELINE_CALIBRATION_PATH",
                                               str(cfg.ROOT / "config" / "camera_calibration.json")))
    baseline = validate_images(image_paths, baseline_calibration, intrinsics_only=True)
    contract["baseline_calibration"] = baseline["calibration"]
    contract["baseline_calibration_sha256"] = baseline["calibration_sha256"]
    return contract


def run_accepted_pipeline(*, session_id, patient_id, image_paths, session_output_dir,
                          manual_intrinsics=None, progress=None) -> Path:
    from src import config as cfg
    def notify(stage, pct, message):
        if progress:
            progress(stage, pct, message)

    contract = preflight(image_paths, manual_intrinsics)
    notify("queued", 0, "等待重建资源...")
    with _GPU_LOCK:
        root = Path(session_output_dir).resolve() / "accepted_c481186"
        root.mkdir(parents=True, exist_ok=False)
        inputs = root / "inputs"
        inputs.mkdir()
        (root / "logs").mkdir()
        (root / "stages").mkdir()
        calibration = inputs / "calibration.json"
        shutil.copy2(cfg.CAMERA_CALIBRATION_PATH, calibration)
        baseline_calibration = inputs / "baseline_calibration.json"
        shutil.copy2(contract["baseline_calibration"], baseline_calibration)
        if sha256(baseline_calibration) != contract["baseline_calibration_sha256"]:
            raise RuntimeError("Baseline calibration changed while copying")
        for view, source in image_paths.items():
            dest = inputs / f"{CAMERA_BY_VIEW[view]}_input.jpg"
            shutil.copy2(source, dest)
            if sha256(dest) != contract["images"][view]["sha256"]:
                raise RuntimeError(f"Input changed while copying: {source}")
        if sha256(calibration) != contract["calibration_sha256"]:
            raise RuntimeError("Calibration changed while copying")
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cfg.ROOT,
                                  capture_output=True, text=True, check=True).stdout.strip()
        manifest = {"pipeline": PIPELINE, "algorithm_base": "c481186", "code_revision": revision,
                    "session_id": session_id, "patient_id": patient_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "inputs": contract, "status": "running", "stages": [],
                    "historical_model_reused": False, "support_rings": 8}
        source_files = list(cfg.ROOT.glob("run_*.py")) + list((cfg.ROOT / "src").rglob("*.py"))
        manifest["source_hashes"] = {str(p.relative_to(cfg.ROOT)): sha256(p) for p in sorted(source_files)}
        manifest["asset_root"] = str(cfg.ASSET_ROOT)
        report = root / "run_manifest.json"
        def save():
            temporary = report.with_suffix(".tmp")
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(report)
        save()
        env = os.environ.copy()
        env.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1",
                   FACE3D_CALIBRATION_PATH=str(calibration),
                   FACE3D_ROMA_TORCH_HOME=os.environ.get("FACE3D_ROMA_TORCH_HOME", str(cfg.MODELS_DIR / "roma-cache")))
        try:
            for index, stage in enumerate(STAGES):
                notify(stage, int(index * 95 / len(STAGES)), f"{index + 1}/{len(STAGES)}: {stage}")
                item = {"name": stage, "status": "running"}
                manifest["stages"].append(item)
                save()
                log_path = root / "logs" / f"{stage}.log"
                with log_path.open("w", encoding="utf-8") as log:
                    result = subprocess.run([sys.executable, "-u", "-m", "src.pipeline.accepted_stages",
                        stage, str(root), str(calibration)], cwd=cfg.ROOT, env=env,
                        stdout=log, stderr=subprocess.STDOUT)
                item["exit_code"] = result.returncode
                if result.returncode:
                    item["status"] = "error"
                    tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-16:])
                    raise RuntimeError(f"Stage {stage} failed. Log: {log_path}\n{tail}")
                item["status"] = "done"
                save()
            model = root / "stages" / "biharmonic" / "meshes" / "face.glb"
            if not model.is_file() or model.stat().st_size < 100:
                raise RuntimeError("Final stage did not publish a model")
            manifest.update(status="done", model=str(model), model_sha256=sha256(model))
            save()
            notify("publishing", 99, "模型已生成，正在保存会话...")
            return model
        except Exception as exc:
            manifest.update(status="error", error=str(exc))
            save()
            raise
