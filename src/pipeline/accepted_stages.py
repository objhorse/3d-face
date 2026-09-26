"""c481186 stage adapter. Executed in a fresh process for each stage."""
from __future__ import annotations

import json
import runpy
import shutil
import sys
from pathlib import Path

from src.pipeline.accepted_capture import capture_images, sha256

STAGES = ("baseline", "projective", "expression", "balanced", "nasal_base",
          "eyelid_texture", "nasal_texture", "alar", "roma", "roma_texture", "biharmonic")


def run_stage(stage: str, root: Path, calibration: Path) -> None:
    from src import config as cfg
    captures = root / "inputs"
    dirs = {name: root / "stages" / name for name in STAGES}
    target = dirs[stage]
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite stage: {target}")
    # Historical baseline used original intrinsics; later nasal stages used v7.
    # Keep this explicit rather than silently applying the later rig upstream.
    cfg.CAMERA_CALIBRATION_PATH = (
        root / "inputs" / "baseline_calibration.json"
        if stage in ("baseline", "projective", "expression") else calibration
    )
    if stage == "baseline":
        cfg.STABLE_USE_CALIBRATED_RIG_EXTRINSICS = False

    def mesh(name, filename):
        return dirs[name] / "meshes" / filename

    def texture(name):
        return dirs[name] / "textures" / "albedo_white.png"

    if stage == "baseline":
        from src.pipeline.stable_three_view import run_stable_three_view_pipeline
        run_stable_three_view_pipeline(session_id=None, patient_id=root.name,
            image_paths=capture_images(captures), session_output_dir=target)
        for view in ("left", "front", "right"):
            initialization = json.loads(
                (target / "debug" / f"init_view_{view}.json").read_text(encoding="utf-8")
            )
            if initialization.get("exp_source") != "initializer":
                raise RuntimeError(
                    f"Historical c481186 baseline requires expression initialization for {view}; "
                    "DECA fallback to zero expression is not an equivalent reconstruction"
                )
    elif stage == "projective":
        sys.argv = ["src.pipeline.stages.projective_texture", "--capture-dir", str(captures),
                    "--baseline", str(dirs["baseline"]), "--output", str(target)]
        runpy.run_module("src.pipeline.stages.projective_texture", run_name="__main__")
    elif stage == "expression":
        from src.pipeline.stages.expression_depth import _export_depth_safe_geometry, _export_with_baseline_texture
        from src.geometry.expression_depth import ExpressionDepthThresholds
        target.mkdir(parents=True)
        report = _export_depth_safe_geometry(source_mesh_dir=dirs["projective"] / "meshes",
            output_mesh_dir=target / "meshes", thresholds=ExpressionDepthThresholds(), cfg=cfg)
        for name in ("cameras.json", "stable_semantic_regions.json"):
            shutil.copy2(mesh("projective", name), target / "meshes" / name)
        (target / "textures").mkdir()
        shutil.copy2(texture("projective"), target / "textures" / "albedo_baseline_locked.png")
        _export_with_baseline_texture(mesh_path=target / "meshes" / "face_mesh.obj",
            texture_path=texture("projective"), output_path=target / "meshes" / "face_same_texture.glb")
        (target / "expression_depth_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    elif stage == "balanced":
        from src.pipeline.stages.balanced_nasal import run_balanced_nasal_shape_experiment
        run_balanced_nasal_shape_experiment(captures, dirs["expression"], target,
            rig_calibration=calibration,
            expected_baseline_glb_sha256=sha256(mesh("expression", "face_same_texture.glb")))
    elif stage == "nasal_base":
        from src.pipeline.stages.nasal_base import run_nasal_base_shape_experiment
        run_nasal_base_shape_experiment(captures, dirs["balanced"], target, rig_calibration=calibration,
            expected_geometry_sha256=sha256(mesh("balanced", "candidate.glb")),
            expected_textured_sha256=sha256(mesh("balanced", "candidate_textured.glb")))
    elif stage == "eyelid_texture":
        from src.pipeline.stages.eyelid_texture import run_absolute_eyelid_texture_experiment
        run_absolute_eyelid_texture_experiment(captures, dirs["nasal_base"], target,
            expected_obj_sha256=sha256(mesh("nasal_base", "face_mesh.obj")),
            expected_geometry_sha256=sha256(mesh("nasal_base", "candidate.glb")),
            expected_textured_sha256=sha256(mesh("nasal_base", "candidate_textured.glb")))
    elif stage == "nasal_texture":
        from src.pipeline.stages.nasal_texture import run_nasal_local_texture_experiment
        run_nasal_local_texture_experiment(captures, dirs["eyelid_texture"], target,
            expected_v2_glb_sha256=sha256(mesh("eyelid_texture", "face.glb")),
            expected_v2_texture_sha256=sha256(texture("eyelid_texture")),
            expected_a2_obj_sha256=sha256(mesh("nasal_base", "face_mesh.obj")))
    elif stage == "alar":
        from src.pipeline.stages.alar_surface import run_multiview_alar_surface_experiment
        run_multiview_alar_surface_experiment(captures, dirs["nasal_base"], dirs["nasal_texture"], target,
            rig_calibration=calibration,
            expected_a2_obj_sha256=sha256(mesh("nasal_base", "face_mesh.obj")),
            expected_v2_glb_sha256=sha256(mesh("eyelid_texture", "face.glb")),
            expected_v2_texture_sha256=sha256(texture("eyelid_texture")))
    elif stage == "roma":
        from src.pipeline.stages.cross_view_observations import run_nasal_texture_observation_audit
        run_nasal_texture_observation_audit(captures, dirs["alar"], target,
            rig_calibration=calibration,
            expected_v10_obj_sha256=sha256(mesh("alar", "face_mesh.obj")),
            expected_v10_report_sha256=sha256(dirs["alar"] / "alar_surface_report.json"),
            expected_rig_sha256=sha256(calibration))
        report = json.loads((target / "metrics.json").read_text(encoding="utf-8"))
        if report.get("status") != "ready_for_geometry":
            raise RuntimeError("RoMa evidence is insufficient; no baseline fallback will be published")
    elif stage == "roma_texture":
        from src.pipeline.stages.roma_texture import run_roma_nasal_texture_rebake
        run_roma_nasal_texture_rebake(captures, dirs["roma"], target,
                                    viewer_vendor_root=cfg.ROOT / "frontend" / "vendor")
    elif stage == "biharmonic":
        from src.pipeline.stages.biharmonic_nasal import run_biharmonic_nasal_geometry_experiment
        run_biharmonic_nasal_geometry_experiment(dirs["roma"], dirs["roma_texture"], dirs["alar"], target,
            support_rings=8, viewer_vendor_root=cfg.ROOT / "frontend" / "vendor")
    else:
        raise ValueError(f"Unknown stage: {stage}")


if __name__ == "__main__":
    import argparse
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("root", type=Path)
    parser.add_argument("calibration", type=Path)
    args = parser.parse_args()
    run_stage(args.stage, args.root.resolve(), args.calibration.resolve())
