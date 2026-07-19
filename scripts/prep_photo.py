from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Final

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    from rembg import remove as rembg_remove
except Exception:  # pragma: no cover - optional dependency
    rembg_remove = None

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUTPUT_PATH: Final[Path] = ROOT / "source-prepped.png"
MAX_DIMENSION: Final[int] = 900
CLAHE_CLIP_LIMIT: Final[float] = 1.8
CLAHE_TILE_GRID: Final[tuple[int, int]] = (8, 8)
SHARPEN_KERNEL: Final[np.ndarray] = np.array(
    [[0.0, -0.8, 0.0], [-0.8, 4.2, -0.8], [0.0, -0.8, 0.0]],
    dtype=np.float32,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove the background, normalize contrast, and prepare a portrait for ASCII conversion."
    )
    parser.add_argument("image_path", type=Path, help="Path to the source portrait image.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output path for the preprocessed grayscale PNG.",
    )
    return parser.parse_args()


def load_image(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Source image not found: {path}")
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGBA")


def remove_background_with_rembg(image: Image.Image) -> Image.Image:
    if rembg_remove is None:
        raise RuntimeError("rembg is not installed")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = rembg_remove(buffer.getvalue())

    if isinstance(result, bytes):
        return Image.open(io.BytesIO(result)).convert("RGBA")
    if isinstance(result, Image.Image):
        return result.convert("RGBA")
    if isinstance(result, np.ndarray):
        return Image.fromarray(result).convert("RGBA")
    raise TypeError(f"Unexpected rembg output type: {type(result)!r}")


def remove_background_grabcut(image: Image.Image) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    height, width = rgb.shape[:2]

    mask = np.zeros((height, width), np.uint8)
    rect = (
        int(width * 0.09),
        int(height * 0.06),
        int(width * 0.82),
        int(height * 0.88),
    )
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)

    cv2.grabCut(rgb, mask, rect, bg_model, fg_model, 5, cv2.GC_INIT_WITH_RECT)
    foreground = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0
    ).astype("uint8")

    alpha = (foreground * 255).astype(np.uint8)
    alpha = cv2.medianBlur(alpha, 5)
    alpha = cv2.GaussianBlur(alpha, (7, 7), 0)

    rgba = cv2.cvtColor(rgb, cv2.COLOR_RGB2RGBA)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, mode="RGBA")


def remove_background(image: Image.Image) -> Image.Image:
    if rembg_remove is not None:
        try:
            print("Removing background with rembg...")
            return remove_background_with_rembg(image)
        except Exception as exc:
            print(
                f"rembg background removal failed, falling back to OpenCV GrabCut: {exc}",
                file=sys.stderr,
            )
    else:
        print("rembg is unavailable, falling back to OpenCV GrabCut...")
    return remove_background_grabcut(image)


def composite_on_white(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, image.convert("RGBA"))


def resize_with_aspect(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    largest = max(width, height)
    if largest <= max_dimension:
        return image

    scale = max_dimension / largest
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def enhance_grayscale(image: Image.Image) -> Image.Image:
    gray = np.array(image.convert("L"))
    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=CLAHE_TILE_GRID,
    )
    enhanced = clahe.apply(gray)
    softened = cv2.GaussianBlur(enhanced, (3, 3), 0)
    sharpened = cv2.filter2D(softened, -1, SHARPEN_KERNEL)
    return Image.fromarray(np.clip(sharpened, 0, 255).astype(np.uint8), mode="L")


def preprocess(image: Image.Image) -> Image.Image:
    segmented = remove_background(image)
    on_white = composite_on_white(segmented)
    resized = resize_with_aspect(on_white, MAX_DIMENSION)
    return enhance_grayscale(resized)


def main() -> int:
    args = parse_args()
    source = args.image_path.resolve()
    output = args.output.resolve() if args.output.is_absolute() else (ROOT / args.output).resolve()

    print(f"Source image: {source}")
    print(f"Output image: {output}")

    try:
        image = load_image(source)
        prepared = preprocess(image)
        output.parent.mkdir(parents=True, exist_ok=True)
        prepared.save(output, format="PNG")
    except Exception as exc:
        print(f"prep_photo.py failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved preprocessed portrait to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

