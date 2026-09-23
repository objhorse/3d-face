# Application Snapshot Cleanup - 2026-09-23

Snapshot publication update: this new `3d-face` repository is exported from
d82a5e9 and initialized independently with one commit. FLAME model pickle files
are excluded. The records below describe preparation in the original repository;
its old commits are NOT ancestors of this new repository's main branch.

## Scope

Packaging-only cleanup on `codex/clean-application-20260923`, derived from
`codex/resume-c481186` at c481186, including the pending frontend/backend adapter.
The independent root checkout and other worktrees are not modified.

Remove tracked local caches, worktree gitlinks, brainstorming server state,
sample photographs/screenshots, personal DOCX files, historical experiment plans,
handoff notes, generated document illustrations and standalone diagnostic tools
from the new snapshot using `git rm --cached`. Keep all of those files on disk.
Keep the source modules required by the application and tests, including modules
whose historical filenames contain `experiment`.

No optimization thresholds, camera mappings, geometry, texture algorithms or
runtime stage order are changed by this cleanup. Existing integration changes
are retained explicitly; this is not a new model-quality acceptance.

## Known Validation Limits

The raw 140210 run with restored DECA completed seven stages, then stopped at
alar preparation because the right alar contour supplied three projected samples.
No complete new v12 model was produced. The UI must not publish its intermediate
mesh as the final result. Historical success and fresh-input success are distinct.

The Windows Matplotlib import-order workaround used by the offline recovery is
not incorporated into the application launcher in this packaging-only change.
Clean-machine dependency installation and full reconstruction remain unverified.

## GitHub Boundary

This cleanup changes the new commit tree, not old history. Previously tracked
photos, caches or licensed assets can remain accessible in old commits. Do not
claim history sanitization or permission to redistribute third-party weights.
No push, visibility change, force push or history rewrite is part of preparation.

## Checks Performed

- 99 tracked items excluded; all local copies verified present.
- 188 retained Python files parsed successfully; no direct imports of excluded
  Python modules found. This is a static check, not proof of all dynamic imports.
- `tests/test_accepted_application.py`: 11 passed in the configured environment.
- `git diff --cached --check`: passed.
- No full GPU reconstruction or fresh-machine installation was run for cleanup.
