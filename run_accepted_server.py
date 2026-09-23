"""Start the c481186 frontend/backend with explicit shared assets and calibration."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--baseline-calibration", type=Path,
                        default=Path(__file__).resolve().parent / "config" / "camera_calibration.json")
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    for path in (args.asset_root, args.calibration, args.baseline_calibration, args.capture_root):
        if not path.exists():
            parser.error(f"Path does not exist: {path}")
    os.environ.update(FACE3D_PIPELINE="accepted_c481186", FACE3D_ASSET_ROOT=str(args.asset_root.resolve()),
                      FACE3D_CALIBRATION_PATH=str(args.calibration.resolve()),
                      FACE3D_BASELINE_CALIBRATION_PATH=str(args.baseline_calibration.resolve()),
                      FACE3D_CAPTURE_ROOT=str(args.capture_root.resolve()))
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///" + (root / "face3d.db").as_posix())
    os.chdir(root)
    import uvicorn
    print(f"c481186 application: http://127.0.0.1:{args.port}/ui/", flush=True)
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
