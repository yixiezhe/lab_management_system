from pathlib import Path

from PIL import Image, ImageOps


SOURCE_DIR = Path(__file__).resolve().parents[1] / "src/views/instrument-booking/images"
OUTPUT_DIR = SOURCE_DIR.parent / "thumbnails"
THUMBNAIL_SIZE = (640, 426)
WEBP_QUALITY = 78


def create_thumbnail(source_path: Path, output_path: Path) -> tuple[int, int]:
    source_size = source_path.stat().st_size
    with Image.open(source_path) as source_image:
        image = ImageOps.exif_transpose(source_image).convert("RGB")
        image = ImageOps.fit(image, THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, "WEBP", quality=WEBP_QUALITY, method=6)
    return source_size, output_path.stat().st_size


def main() -> None:
    source_paths = sorted(SOURCE_DIR.glob("*.jpg"))
    if not source_paths:
        raise SystemExit(f"No JPG images found in {SOURCE_DIR}")

    total_source = 0
    total_output = 0
    for source_path in source_paths:
        output_path = OUTPUT_DIR / f"{source_path.stem}.webp"
        source_size, output_size = create_thumbnail(source_path, output_path)
        total_source += source_size
        total_output += output_size
        print(f"{source_path.name}: {source_size:,} -> {output_size:,} bytes")

    reduction = (1 - total_output / total_source) * 100
    print(f"Total: {total_source:,} -> {total_output:,} bytes ({reduction:.1f}% smaller)")


if __name__ == "__main__":
    main()
