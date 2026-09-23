"""Validated, anatomical camera inputs for the c481186 application."""
from __future__ import annotations

import hashlib
from pathlib import Path

CAMERA_BY_VIEW = {"left": "camera1", "front": "camera2", "right": "camera3"}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_images(directory: Path, *, allowed_root: Path | None = None) -> dict[str, Path]:
    directory = Path(directory).resolve(strict=True)
    if allowed_root is not None and not _inside(directory, allowed_root):
        raise ValueError("Capture directory is outside FACE3D_CAPTURE_ROOT")
    if not directory.is_dir():
        raise ValueError("Capture path must be a directory")
    result = {}
    for view, camera in CAMERA_BY_VIEW.items():
        matches = sorted(directory.glob(f"{camera}_*.jpg"))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {camera}_*.jpg; found {len(matches)}")
        path = matches[0].resolve(strict=True)
        if allowed_root is not None and not _inside(path, allowed_root):
            raise ValueError("Capture image resolves outside FACE3D_CAPTURE_ROOT")
        result[view] = path
    return result


def validate_images(images: dict[str, Path], calibration: Path, *, intrinsics_only=False) -> dict:
    from PIL import Image
    from src.geometry.profile_triangulation import load_profile_rig

    if set(images) != set(CAMERA_BY_VIEW):
        raise ValueError("Exactly left, front and right images are required")
    rig = load_profile_rig(calibration, expected_camera_by_view=CAMERA_BY_VIEW,
                           max_stereo_rms_px=float("inf") if intrinsics_only else 10.0)
    items = {}
    for view, path in images.items():
        with Image.open(path) as image:
            size = image.size
            image.verify()
        expected = tuple(rig.cameras_by_view[view].image_size)
        if size != expected:
            raise ValueError(f"{view}: image size {size} differs from calibration {expected}")
        items[view] = {"camera": CAMERA_BY_VIEW[view], "name": path.name,
                       "size": list(size), "sha256": sha256(path)}
    return {"images": items, "calibration": str(calibration.resolve()),
            "calibration_sha256": sha256(calibration)}
