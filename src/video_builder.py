from pathlib import Path
import subprocess

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    FPS,
)


class VideoBuilder:

    def __init__(self):
        pass

    # ---------------------------------------------------------

    def build(
        self,
        video_path,
        output_path,
        duration
    ):

        vf = (

            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            f"force_original_aspect_ratio=increase,"

            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"

            f"fps={FPS},"

            # STOCK FOOTAGE label — bottom right
            # STOCK FOOTAGE label — animated bottom right
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "text='STOCK FOOTAGE':"
            "x=w-tw-45:"
            "y=h-th-45+if(lt(t\,0.35)\,20*(1-t/0.35)\,0):"
            "fontsize=35:"
            "fontcolor=yellow:"
            "box=1:"
            "boxcolor=black@0.55:"
            "boxborderw=8:"
            "alpha=if(lt(t\,0.35)\,t/0.35\,1)"

        )

        cmd = [

            "ffmpeg",

            "-y",

            "-stream_loop",
            "-1",

            "-i",
            str(video_path),

            "-t",
            f"{duration + 0.05:.3f}",

            "-vf",
            vf,

            "-an",

            "-c:v",
            "h264_nvenc",

            "-preset",
            "medium",

            "-cq",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-r",
            str(FPS),

            "-movflags",
            "+faststart",

            str(output_path)

        ]

        subprocess.run(
            cmd,
            check=True
        )