# 3D Face

Three-view face reconstruction with a FastAPI backend and a static browser UI.
The backend serves the frontend at `/ui/`; a separate frontend server is not needed.

## Entry Points

| Entry | Purpose | Status |
| --- | --- | --- |
| `run_server.py` | Existing application / default configured pipeline | Legacy entry, not a v12 result guarantee |
| `run_accepted_server.py` | Explicit c481186 stage integration | Raw-photo full chain is NOT validated |
| `python -m src.cli.stable` | Offline stable reconstruction | Separate from the complete v12 chain |

Do not interpret the internal name `accepted_c481186` as acceptance of a new
dataset's output. Historical v12 final-stage reproduction used saved upstream
intermediates. It did not validate reconstruction from fresh photographs.

## Layout

- `frontend/`: UI, model viewer, bundled browser dependencies.
- `src/api/`: HTTP API, database, job execution and progress reporting.
- `src/pipeline/`: reconstruction orchestration and input validation.
- `src/pipeline/stages/`: internal stage implementations, not root debug scripts.
- `src/cli/`: offline command-line entry points.
- `src/geometry/`, `src/appearance/`, `src/initializers/`: reconstruction algorithms.
- `config/`: calibration and configuration files.
- `tests/`: automated regression and contract tests.
- `tools/`: retained calibration, evaluation and asset utilities.
- `docs/c481186-application.md`: integration configuration and validation limits.

The root contains only the two server launchers. Required former experiment
modules now live in `src/pipeline/stages/`; algorithm function names and stage
ordering are preserved. Independent unused experiment entry points are excluded.
See [the layout record](docs/application-layout.md) for migration and verification.

## Run Locally

Start with [configuration on another machine](docs/deployment.md): environments,
weight layout, anatomical camera mapping, calibration, and the two launchers.

Use the existing configured Python environment with the model assets installed.
`requirements.txt` is a supplemental dependency list, NOT a complete environment
lockfile; this checkout has not been validated as a clean-machine installation.

```powershell
python run_server.py
```

Open `http://127.0.0.1:8000/ui/`. API documentation is at `/docs`.
For the separate c481186 integration, see [its guide](docs/c481186-application.md).
Do not point the legacy launcher at an output directory and assume it runs v12.

Camera naming is anatomical: camera1 = subject's left, camera2 = front,
camera3 = subject's right. Calibration must match the actual rig and image sizes.

## Assets And Submission Boundary

Capture photographs, generated meshes/viewers, databases, model caches, local
worktrees, one-off diagnostic tools and historical experiment notes are excluded
from this snapshot. This repository starts with one independent initial commit,
exported from source revision d82a5e9. The original repository's history is not
included; its local files and original remote remain unchanged.

Model weights and external repositories must be obtained under their own licenses.
FLAME model pickle files are excluded along with other model weights. This
snapshot does not grant rights to redistribute third-party assets.

See [the cleanup record](docs/release-cleanup-20260923.md) for exact scope and limits.
