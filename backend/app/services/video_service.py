"""
Video composition service using moviepy.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from moviepy.editor import (
    AudioFileClip,
    TextClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Limit concurrent video processing to avoid OOM
video_executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_video_jobs)


class VideoService:
    """Service for composing videos."""

    def __init__(self):
        self.output_dir = Path(settings.static_dir) / "video"
        self.static_base = Path(settings.static_dir)

    async def create_video(
        self,
        project_id: str,
        audio_files: List[str],
        meta_data: List[dict],
        image_files: List[str] = None,
    ) -> str:
        """
        Componse final video from audio clips and text overlays.
        Runs in a separate thread to not block the async event loop.
        """
        loop = asyncio.get_running_loop()

        full_audio_paths = [self.static_base / path for path in audio_files]

        # Get image paths if provided
        full_image_paths = None
        if image_files:
            full_image_paths = [self.static_base / path for path in image_files]

        # Determine full paths
        project_video_dir = self.output_dir / str(project_id)
        project_video_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_video_dir / "final.mp4"

        try:
            logger.info(
                "Starting video composition",
                project_id=project_id,
                clips=len(audio_files),
            )

            # Execute blocking moviepy code in thread pool
            await loop.run_in_executor(
                video_executor,
                self._compose_video_sync,
                full_audio_paths,
                meta_data,
                output_path,
                full_image_paths,
            )

            # Return relative path
            relative_path = output_path.relative_to(self.static_base)
            return str(relative_path).replace("\\", "/")

        except Exception as e:
            logger.error(
                "Video composition failed", project_id=project_id, error=str(e)
            )
            raise

    def _compose_video_sync(
        self,
        audio_paths: List[Path],
        meta_data: List[dict],
        output_path: Path,
        image_paths: List[Path] = None,
    ) -> None:
        """Blocking moviepy video composition logic with Ken Burns effect."""

        clips = []
        for i, (audio_path, meta) in enumerate(zip(audio_paths, meta_data)):
            if not audio_path.exists():
                logger.warning(f"Audio file missing: {audio_path}")
                continue
            # Create audio clip
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.5
            # Get image or use solid color fallback
            if (
                image_paths
                and i < len(image_paths)
                and image_paths[i]
                and image_paths[i].exists()
            ):
                # Use generated image with Ken Burns effect
                video_clip = self._create_ken_burns_clip(str(image_paths[i]), duration)
            else:
                # Fallback: solid color background
                bg_color = (20, 20, 30)
                video_clip = ColorClip(
                    size=(1280, 720), color=bg_color, duration=duration
                )
            # Create text overlay
            try:
                txt_clip = (
                    TextClip(
                        f"{meta['speaker']}\n\n{meta['line']}",
                        fontsize=30,
                        color="white",
                        font="Arial-Bold",
                        size=(1000, 600),
                        method="caption",
                        align="center",
                    )
                    .set_position("center")
                    .set_duration(duration)
                )
                video_clip = CompositeVideoClip([video_clip, txt_clip])
            except Exception:
                logger.warning("TextClip failed, using plain background")

            video_clip = video_clip.set_audio(audio_clip)
            clips.append(video_clip)

        if not clips:
            raise ValueError("No valid clips to concatenate")

        final_video = concatenate_videoclips(clips, method="compose")

        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger=None,
        )

        final_video.close()
        for clip in clips:
            clip.close()

    def _create_ken_burns_clip(self, image_path: str, duration: float):
        """Create a clip with Ken Burns (zoom/pan) effect."""
        from moviepy.editor import ImageClip
        import random

        # Load image
        img_clip = ImageClip(image_path)

        # Random zoom direction (zoom in or out)
        zoom_in = random.choice([True, False])

        if zoom_in:
            # Start at 100%, end at 110%
            start_scale = 1.0
            end_scale = 1.1
        else:
            # Start at 110%, end at 100%
            start_scale = 1.1
            end_scale = 1.0

        # Random pan direction
        pan_x = random.uniform(-0.05, 0.05)
        pan_y = random.uniform(-0.05, 0.05)

        def resize_func(t):
            progress = t / duration
            scale = start_scale + (end_scale - start_scale) * progress
            return scale

        def position_func(t):
            progress = t / duration
            x_offset = int(1280 * pan_x * progress)
            y_offset = int(720 * pan_y * progress)
            return ("center", "center")

        # Apply zoom effect
        final_clip = img_clip.resize(lambda t: resize_func(t))
        final_clip = final_clip.set_duration(duration)
        final_clip = final_clip.set_position(position_func)

        # Crop to target size
        final_clip = CompositeVideoClip(
            [final_clip.set_position("center")], size=(1280, 720)
        ).set_duration(duration)

        return final_clip


# Singleton instance
video_service = VideoService()
