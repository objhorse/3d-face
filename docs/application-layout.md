# Application Layout

Only `run_server.py` and `run_accepted_server.py` remain as root Python files.
Their API, URLs, pipeline selection and command arguments are unchanged.

## Runtime Modules

The c481186 adapter imports implementations from `src.pipeline.stages`:

| Stage | Module |
| --- | --- |
| Projective texture | `projective_texture` |
| Expression depth | `expression_depth` |
| Balanced nasal | `balanced_nasal` |
| Nasal base | `nasal_base` |
| Eyelid texture | `eyelid_texture` |
| Nasal texture | `nasal_texture` |
| Alar surface | `alar_surface` |
| Cross-view observations | `cross_view_observations` |
| RoMa texture | `roma_texture` |
| Biharmonic surface | `biharmonic_nasal` |

Shared stage helpers are `multiview_nasal` and `nasal_observations`. Calibrated
rendering is `src.reports.calibrated_model_views`. None require top-level
`run_*_experiment.py` modules. Resource locations still resolve from the repository
root, not the new stage directory. The worker remains in `src/geometry/`.

Offline stable reconstruction is retained as:

```powershell
python -m src.cli.stable --capture-dir E:\captures\sample --output-dir E:\results\sample
```

## Scope

Fourteen unused standalone root scripts were removed from the release tree,
along with two test modules solely for removed diagnostic/experimental entry
points. Local archived copies are kept outside the repository. Tests of retained
runtime stages are preserved and updated to use package imports.

The stage algorithms, function signatures, numerical thresholds, camera mapping,
frontend, API and output schemas are unchanged. Internal module import paths and
source-hash manifest filenames necessarily change. This refactor does not resolve
the documented alar failure or establish full v12 reconstruction success.

## Verification (2026-09-26)

- Before relocation: 73 targeted application/stage tests passed.
- After relocation: the same tests plus 7 layout regressions passed (80 total).
- Entire retained test suite: 570 passed.
- UI, app JavaScript, Three.js, runtime API and session-list API: HTTP 200 through
  FastAPI TestClient with an in-memory database.
- Accepted-server, offline stable, and projective-stage help commands succeeded.
- Frontend, API, both server launchers, geometry and appearance core files are
  unchanged from the initial snapshot.
- No full GPU reconstruction or browser visual acceptance was performed for this
  structural-only change. Existing reconstruction limitations still apply.
