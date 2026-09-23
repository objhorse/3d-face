# Running From Another Checkout

This project is source code, not an installer or a packaged application. Prepare
your own Python environments, licensed weights and capture-rig calibration.
Run commands from the repository root. No original D: drive layout is required.

## Important Status

The web application and the reconstruction are separate validation boundaries.
Starting the UI does not establish that a full reconstruction will succeed.
The c481186 raw-photo chain currently stops at alar preparation on the latest
140210 test; no new complete v12 result has passed validation. Configuring all
dependencies does not resolve that algorithm/data limitation.

## Environments

`requirements-web.txt` lists the directly used web dependencies. Install them
into the environment used to start the server:

```powershell
python -m pip install -r requirements-web.txt
```

Reconstruction also needs its numerical, vision and third-party dependencies.
The following versions are observations from the existing machine, NOT a tested
fresh-install lockfile. Do not blindly copy its entire environment: it contains
both OpenCV distributions and accumulated dependency conflicts.

| Component | Main reconstruction environment | Separate RoMa environment |
| --- | --- | --- |
| Python | 3.8.20 | 3.11.9 |
| torch | 2.4.1+cu118 | 2.3.1 |
| torchvision | 0.19.1+cu118 | 0.18.1 |
| numpy / scipy | 1.24.4 / 1.10.1 | numpy 1.26.4 |
| mediapipe / face-alignment | 0.10.9 / 1.4.1 | not used by worker |
| insightface / onnxruntime-gpu | 0.7.3 / 1.19.2 | not used by worker |
| trimesh / Pillow / matplotlib | 4.11.5 / 10.4.0 / 3.7.5 | Pillow 10.3.0 |
| kornia / einops / yacs | 0.7.3 / 0.8.1 / 0.1.8 | kornia 0.7.3, einops 0.8.2 |
| chumpy / scikit-image / scikit-learn | 0.70 / 0.21.0 / 1.3.2 | not used by worker |
| romatch / timm | use separate worker | 0.1.2 / 1.0.25 |

RoMa requires a CUDA-capable environment. MICA's InsightFace detector uses the
CPU execution provider even when the MICA torch model uses CUDA. Prepare the
external repositories' own dependencies too. The old `requirements.txt` remains
a historical supplemental list (including a different MediaPipe pin), not an
authoritative recipe for reproducing this environment.

## Assets

By default assets live in the checkout. Set `FACE3D_ASSET_ROOT` to use another
directory containing both `models/` and `external/`:

```text
ASSET_ROOT/
  models/FLAME/generic_model.pkl
  models/FLAME/landmark_embedding.npy
  models/DECA/deca_model.tar
  models/MICA/mica.tar
  models/roma-cache/hub/checkpoints/roma_outdoor.pth
  models/roma-cache/hub/checkpoints/dinov2_vitl14_pretrain.pth
  external/DECA/       (decalib and its required data)
  external/MICA/       (micalib, configs, utils and its required data)
```

FLAME topology/UV/landmark assets required by DECA and MICA must also be prepared
according to those repositories; the above list is not a replacement for their
asset setup. Do not mix arbitrary FLAME topology versions. Obtain all assets
under their own licenses; the project does not grant redistribution rights.
Face-alignment may also download its detector/landmark weights into the torch
cache on first use, so an offline machine must prepare that cache beforehand.

InsightFace expects `models/antelopev2/*.onnx` under `FACE3D_INSIGHTFACE_ROOT`.
The default is the current user's `~/.insightface`, not the original author's
home directory. Set the environment variable BEFORE starting the server.

## Configuration And Start

Replace these example paths with your own existing directories/files:

```powershell
$env:FACE3D_ASSET_ROOT = 'E:\face-assets'
$env:FACE3D_INSIGHTFACE_ROOT = 'E:\face-assets\insightface'
$env:FACE3D_ROMA_PYTHON = 'E:\envs\roma\python.exe'
$env:FACE3D_ROMA_TORCH_HOME = 'E:\face-assets\models\roma-cache'

python run_accepted_server.py `
  --asset-root $env:FACE3D_ASSET_ROOT `
  --capture-root 'E:\captures' `
  --baseline-calibration 'E:\calibration\baseline.json' `
  --calibration 'E:\calibration\nasal-rig.json' `
  --port 8012
```

Open `http://127.0.0.1:8012/ui/`. Backend and frontend use the same port.
If `FACE3D_ROMA_PYTHON` is unset, the current Python executable is used; this is
only suitable if it also has RoMa and CUDA configured. It no longer selects a
hard-coded Conda environment on another machine.

For the legacy/default pipeline, use `python run_server.py` and port 8000.
This is NOT interchangeable with the c481186 launcher. Both read the same
source checkout, but select different orchestration paths.

The c481186 launcher binds to localhost. This application is intended for local
use; it has no production authentication layer. Do not expose it publicly merely
by changing the bind address. The directory-input API is loopback-only.

## Inputs And Calibration

Each capture directory needs exactly one `camera1_*.jpg`, `camera2_*.jpg` and
`camera3_*.jpg`. Camera1 is anatomical left, camera2 front, camera3 anatomical
right. The directory must be inside the configured capture root.

Calibration must match your rig and photograph dimensions. The two calibration
arguments preserve historical stage roles, NOT a recommendation to swap left
and right. The old later-stage calibration was stored in an ignored output
directory and is NOT supplied by a normal clone. Users must provide it explicitly
or provide an appropriate calibration for their own data; the repository's sample
calibration is not a universal replacement.

## Verification And Known Blockers

```powershell
python -c "from src.api.app import app; print(app.title)"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
& $env:FACE3D_ROMA_PYTHON -c "import torch, romatch; print(torch.cuda.is_available())"
```

The first command verifies API import only. The CUDA checks do not load weights.
Open `/api/runtime` to verify the active pipeline and calibration. Use a NEW
session/output for each trial. Only a completed final stage publishes the v12 GLB;
an intermediate viewer is not a successful final reconstruction.

On the existing Windows setup, a Matplotlib DLL/import-order problem required an
offline preload workaround. This has not been solved by the portability edits.
See `docs/c481186-application.md` for this and the current alar-stage failure.
No clean-machine GPU end-to-end verification is claimed.
