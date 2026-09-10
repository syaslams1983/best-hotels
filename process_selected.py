
from pathlib import Path
import subprocess
import sys

from select_images import select_hotel
from src.timeline_builder import TimelineBuilder
from src.renderer import Renderer
from src.transcript import TranscriptGenerator

BASE_DIR = Path("input/images")
REALESRGAN_SCRIPT = Path("/kaggle/working/Real-ESRGAN/inference_realesrgan.py")

_TRANSCRIPT_CACHE = {}
_ORIGINAL_TRANSCRIBE = TranscriptGenerator.transcribe


def _cached_transcribe(self, audio_file):
    key = str(Path(audio_file).resolve())
    if key in _TRANSCRIPT_CACHE:
        print(f"[Transcript] Reusing cached transcript: {audio_file}")
        return _TRANSCRIPT_CACHE[key]

    segments = _ORIGINAL_TRANSCRIBE(self, audio_file)
    _TRANSCRIPT_CACHE[key] = segments
    return segments


TranscriptGenerator.transcribe = _cached_transcribe


def get_selected_images(hotel_number):
    selection_file = Path(f"selected_images_{hotel_number}.txt")
    if not selection_file.exists():
        return []

    selected = []
    seen = set()

    for raw_line in selection_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        # Expected select_images.py output:
        # 01 | intro.jpg | score=1.000 | 0.00-3.00 | text...
        parts = [p.strip() for p in line.split("|")]

        if len(parts) < 2:
            continue

        # First column must be a numeric sequence number.
        if not parts[0].isdigit():
            continue

        name = parts[1]

        # Accept only actual image filenames.
        if Path(name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue

        # Never feed already-upscaled files back into Real-ESRGAN.
        if Path(name).stem.endswith("_out"):
            continue

        if name not in seen:
            seen.add(name)
            selected.append(name)

    return selected


def upscale_hotel(hotel_dir, selected):
    images_dir = hotel_dir / "images"
    upscaled_dir = hotel_dir / "selected_upscaled"
    upscaled_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "-" * 40)
    print(f"Upscaling Hotel {hotel_dir.name}")
    print("-" * 40)

    for filename in selected:
        src = images_dir / filename

        if not src.exists():
            print(f"[Skip missing] {filename}")
            continue

        expected_output = upscaled_dir / f"{Path(filename).stem}_out{Path(filename).suffix}"

        if expected_output.exists():
            print(f"[Skip already upscaled] {expected_output.name}")
            continue

        print(f"[Upscale] {filename}")

        cmd = [
            sys.executable,
            str(REALESRGAN_SCRIPT),
            "-n", "RealESRGAN_x4plus",
            "-i", str(src),
            "-o", str(upscaled_dir),
        ]

        result = subprocess.run(cmd)

        if result.returncode != 0:
            raise RuntimeError(
                f"Real-ESRGAN failed for Hotel {hotel_dir.name}: {filename}"
            )

    return upscaled_dir


def render_hotel(hotel_dir, output_dir):
    audio_file = hotel_dir / "voice.mp3"
    images_dir = hotel_dir / "selected_upscaled"
    output_file = output_dir / f"hotel_{hotel_dir.name}.mp4"

    print("\n" + "-" * 40)
    print(f"Rendering Hotel {hotel_dir.name}")
    print("-" * 40)

    builder = TimelineBuilder(
        audio_file=audio_file,
        images_dir=images_dir,
    )

    timeline = builder.build()

    renderer = Renderer()
    renderer.render(
        timeline=timeline,
        audio_file=audio_file,
        output_file=output_file,
        hotel_number=hotel_dir.name,
    )

    print(f"[DONE] {output_file}")


def main():
    start_hotel = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    hotels = [
        folder for folder in BASE_DIR.iterdir()
        if folder.is_dir()
        and folder.name.isdigit()
        and int(folder.name) >= start_hotel
    ]
    hotels.sort(key=lambda p: int(p.name))

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for hotel_dir in hotels:
        output_file = output_dir / f"hotel_{hotel_dir.name}.mp4"

        if output_file.exists():
            print(f"[Skip] Hotel {hotel_dir.name} already rendered")
            continue

        print("\n" + "=" * 60)
        print(f"STARTING HOTEL {hotel_dir.name}")
        print("=" * 60)

        audio_key = str((hotel_dir / "voice.mp3").resolve())
        _TRANSCRIPT_CACHE.pop(audio_key, None)

        # Whisper runs here once.
        select_hotel(hotel_dir)

        selected = get_selected_images(hotel_dir.name)
        print(f"\nHotel {hotel_dir.name}: {len(selected)} selected original images")

        if not selected:
            print(f"[Skip] No selected images for Hotel {hotel_dir.name}")
            continue

        # Upscale originals only.
        upscale_hotel(hotel_dir, selected)

        # TimelineBuilder reuses cached transcript here.
        render_hotel(hotel_dir, output_dir)

        _TRANSCRIPT_CACHE.pop(audio_key, None)

        print("\n" + "=" * 60)
        print(f"HOTEL {hotel_dir.name} COMPLETE")
        print("=" * 60)

    print("\nALL REQUESTED HOTELS COMPLETE")


if __name__ == "__main__":
    main()
