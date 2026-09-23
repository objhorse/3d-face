# c481186 Application Integration

## Scope

The application runs the algorithms from c481186 on fresh captures. It does not
replay historical face outputs. It is not a claim of byte-identical reconstruction
from raw images: the historical baseline was an existing intermediate result.
The previous v12 reproduction only established identity of the final-stage output.

## Data Flow

Directory or uploads -> validated input snapshot -> stable baseline -> strict
projective texture -> protected expression -> balanced nasal v4 -> nasal base ->
absolute eyelid texture -> local nasal texture -> alar surface -> RoMa observations
and geometry -> RoMa texture -> vector biharmonic (support rings 8).

Each stage runs in a separate process using the same checkout. Expected hashes
are computed from this run's upstream outputs, retaining mutation checks without
locking the pipeline to a historical subject. Stages stop on failure; no baseline
is substituted for a failed final result. GPU jobs are serialized in one server.

## Start

From this checkout, in PowerShell:

```powershell
D:\Anaconda\envs\gaussian\python.exe run_accepted_server.py `
  --asset-root D:\face3D `
  --capture-root D:\face3D `
  --calibration D:\face3D\output\calibration\joint_multi_dataset_rig_v7_triplet_scale\camera_calibration_joint_candidate.json `
  --port 8012
```

Open http://127.0.0.1:8012/ui/. Create a reconstruction, enter a capture directory,
inspect the photos, and start. The existing upload path uses the same pipeline.
camera1 is anatomical left, camera2 front, camera3 anatomical right.
The supplied calibration must match the physical capture rig and image sizes.

Historical calibration roles are distinct: baseline/projective/expression used
the checkout's config/camera_calibration.json intrinsics and free pose fitting;
later nasal stages used joint_multi_dataset_rig_v7_triplet_scale. The two files
exchange side-camera intrinsics. This integration preserves and records that
historical distinction; it does not establish that both physically represent
the rig correctly. --baseline-calibration overrides the first file explicitly.
Neither input photographs nor anatomical camera labels are swapped.

Asset root shares model weights and third-party dependencies only, not historical
reconstruction outputs. FACE3D_ROMA_PYTHON can select the RoMa environment;
FACE3D_ROMA_TORCH_HOME can select its weight cache.

The original run_server.py retains its existing default. Use run_accepted_server.py
to select the integrated method explicitly; the UI displays the active pipeline.

## Outputs And Validation

Each session stores snapshots, per-stage logs and run_manifest.json under
output/sessions/ID/accepted_c481186. Its final model is
stages/biharmonic/meshes/face.glb. The web viewer loads that exact final file.
No output is overwritten. Failures remain inspectable from their stage logs.

Contract tests cover camera mapping, ambiguous/out-of-root directory rejection,
stage ordering, failure propagation, overwrite protection, API input and model
publication. Full raw-input reconstruction and visual validation must also pass
before claiming parity or multi-dataset generalization.

## Validation Status (2026-09-20)

The raw captures_20260612_135253 API run is session 3. Baseline, projective,
expression, balanced, nasal_base, eyelid_texture, and nasal_texture completed.
Nasal-base validation reported zero new face flips. The alar profile solver
failed to converge at its original 600-evaluation budget. The API correctly
records failure and does not offer an intermediate model as the final result.

An isolated diagnostic at 1800 evaluations also failed (profile residual cost
153.2664 -> 153.0895). A central-difference diagnostic failed in the front stage;
the production solver and its acceptance criteria remain unchanged. These
experiments do not prove a numerical-precision cause. Reports are in session 3's
accepted_c481186 directory as alar_budget_600.json, alar_budget_1800.json, and
alar_central_budget_600.json. Future alar failures now retain a structured
optimization_failure.json with input hashes, config, and stage results.

The full raw-photo chain is NOT yet validated. Historical final-stage replay
success must not be presented as full application success. Next, reconcile the
fresh upstream baseline and observation contracts with the historical chain
before changing optimizer behavior or claiming generalization.

### Earliest Confirmed Input Divergence

Comparing historical controlled_identity_v1/debug against session 3 baseline/debug:
init_mica_shape.json and all three *_landmarks.png files have identical SHA256.
All three init_view_*.json files differ. Historical front initialization records
exp_source=initializer; the new front records exp_source=zero and a different
R_init/t_init. The current log explicitly reports missing
D:/face3D/models/DECA/deca_model.tar and fallback to face_alignment pose.
This establishes non-equivalent initialization, not yet proof that restoring
DECA alone resolves all downstream differences.

Accepted-mode preflight now requires DECA_MODEL_PATH. After baseline execution,
all three views must report exp_source=initializer before later stages run.
Eleven application tests passed on 2026-09-20, including missing-weight and
zero-expression fallback rejection. Production optimization is unchanged.

### Update (2026-09-23)

DECA weights have been restored and encoder-only inference succeeded for all
three views in the fresh 140210 run. The restored checkpoint has SHA256
E714ED293054CBA5EEA9C96BD3B6B57880074CD84B3FD00D606CBAF0BEE7C5C2;
its identity with the historical checkpoint is unknown.

That run completed the first seven stages, then failed in alar preparation:
front_subject_right_alar had only three projected samples. RoMa and biharmonic
did not run. The nasal_texture GLB is an intermediate, not a final v12 result.
An offline Matplotlib preload workaround was needed for Windows DLL loading;
that workaround is not yet integrated into the server entry point.

No historical expression vectors or meshes were substituted for inference.
The full raw-photo application chain remains unvalidated.
