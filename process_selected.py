from pathlib import Path
import shutil
import subprocess
import sys

from src.timeline_builder import TimelineBuilder
from src.renderer import Renderer
from select_images import select_hotel

BASE_DIR = Path("input/images")
SELECTED_PREFIX = "selected_images_"

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp",
}

def get_selected_images(hotel_number):
    selected_file = Path(f"{SELECTED_PREFIX}{hotel_number}.txt")
    if not selected_file.exists():
        raise RuntimeError(f"Missing selection file: {selected_file}")

    images = []
    for line in selected_file.read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        filename = parts[1].strip()
        if Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        images.append(filename)
    return images

def upscale_hotel(hotel_dir, selected_images):
    source_dir = hotel_dir / "images"
    work_dir = hotel_dir / "selected_upscaled"
    work_dir.mkdir(parents=True, exist_ok=True)

    print("\n----------------------------------------")
    print(f"Upscaling Hotel {hotel_dir.name}")
    print("----------------------------------------")

    for filename in selected_images:
        source = source_dir / filename
        output = work_dir / f"{Path(filename).stem}_out{Path(filename).suffix}"

        if not source.exists():
            print(f"[Missing] {filename}")
            continue
        if output.exists():
            print(f"[Skip] {filename}")
            continue

        print(f"[Upscale] {filename}")

        command = [
            sys.executable,
            "/kaggle/working/Real-ESRGAN/inference_realesrgan.py",
            "-n", "RealESRGAN_x4plus",
            "-i", str(source),
            "-o", str(work_dir),
        ]
        subprocess.run(command, check=True)

    return work_dir

def prepare_render_images(hotel_dir, upscaled_dir):
    images_dir = hotel_dir / "images"
    backup_dir = hotel_dir / "original_images_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print("\nPreparing render images...")

    for image in images_dir.iterdir():
        if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS:
            backup = backup_dir / image.name
            if not backup.exists():
                shutil.copy2(image, backup)

    for image in images_dir.iterdir():
        if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS:
            image.unlink()

    for image in upscaled_dir.iterdir():
        if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS:
            shutil.copy2(image, images_dir / image.name)
            print(f"[Render] {image.name}")

def render_hotel(hotel_dir, output_dir):
    hotel_number = hotel_dir.name
    audio_file = hotel_dir / "voice.mp3"
    images_dir = hotel_dir / "images"

    if not audio_file.exists():
        print(f"[Skip] Hotel {hotel_number}: voice.mp3 missing")
        return

    print("\n========================================")
    print(f"RENDERING HOTEL {hotel_number}")
    print("========================================")

    builder = TimelineBuilder(
        audio_file=audio_file,
        images_dir=images_dir,
    )
    timeline = builder.build()

    output_file = output_dir / f"hotel_{hotel_number}.mp4"

    renderer = Renderer()
    renderer.render(
        timeline=timeline,
        audio_file=audio_file,
        output_file=output_file,
        hotel_number=int(hotel_number),
    )

    print(f"[INFO] Hotel #{hotel_number} saved : {output_file}")

def main():
    hotels = [
        folder for folder in BASE_DIR.iterdir()
        if folder.is_dir() and folder.name.isdigit()
    ]
    hotels.sort(key=lambda p: int(p.name))

    if not hotels:
        raise RuntimeError("No hotel folders found.")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for hotel_dir in hotels:
        print("\n" + "=" * 60)
        print(f"STARTING HOTEL {hotel_dir.name}")
        print("=" * 60)

        # 1) Whisper transcript + image selection for this hotel only.
        select_hotel(hotel_dir)

        # 2) Read this hotel's fresh selection.
        selected = get_selected_images(hotel_dir.name)
        print(f"\nHotel {hotel_dir.name}: {len(selected)} selected images")

        if not selected:
            print(f"[Skip] No selected images for Hotel {hotel_dir.name}")
            continue

        # 3) Upscale only this hotel's selected images.
        upscaled_dir = upscale_hotel(hotel_dir, selected)

        # 4) Prepare and render this hotel before moving to the next.
        prepare_render_images(hotel_dir, upscaled_dir)
        render_hotel(hotel_dir, output_dir)

        print(f"\nHotel {hotel_dir.name} COMPLETE")
        print("=" * 60)

    print("\n" + "=" * 60)
    print("ALL HOTELS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()