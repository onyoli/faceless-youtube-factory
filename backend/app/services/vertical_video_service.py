"""
Vertical Video Service for Shorts/TikTok.
Optimized for fast rendering with FFmpeg-based composition.
"""

import asyncio
import subprocess
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from moviepy.editor import AudioFileClip

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Dedicated executor for video processing
vertical_video_executor = ThreadPoolExecutor(max_workers=1)

# Video dimensions (9:16 vertical) - use 720p for faster rendering
WIDTH = 720
HEIGHT = 1280


class VerticalVideoService:
    """Service for creating vertical videos for Shorts/TikTok."""

    def __init__(self):
        self.static_base = Path(settings.static_dir)
        self.output_dir = self.static_base / "shorts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.static_base / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def create_vertical_video(
        self,
        project_id: str,
        audio_files: List[str],
        meta_data: List[dict],
        image_files: List[str] = None,
        image_scene_indices: List[int] = None,
        background_video_url: Optional[str] = None,
        background_music_url: Optional[str] = None,
        music_volume: float = 0.3,
        enable_captions: bool = True,
    ) -> str:
        """Create a vertical video optimized for speed."""
        try:
            output_path = self.output_dir / f"{project_id}.mp4"

            audio_paths = [self.static_base / p for p in audio_files]
            bg_video_path = (
                self.static_base / background_video_url
                if background_video_url
                else None
            )
            bg_music_path = (
                self.static_base / background_music_url
                if background_music_url
                else None
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                vertical_video_executor,
                self._compose_fast,
                project_id,
                audio_paths,
                meta_data,
                output_path,
                bg_video_path,
                bg_music_path,
                music_volume,
                enable_captions,
            )

            relative_path = output_path.relative_to(self.static_base)
            return str(relative_path).replace("\\", "/")

        except Exception as e:
            logger.error(
                "Vertical video composition failed", project_id=project_id, error=str(e)
            )
            raise

    def _compose_fast(
        self,
        project_id: str,
        audio_paths: List[Path],
        meta_data: List[dict],
        output_path: Path,
        bg_video_path: Optional[Path],
        bg_music_path: Optional[Path],
        music_volume: float,
        enable_captions: bool,
    ) -> None:
        """Fast composition using FFmpeg directly."""
        start_time = time.time()

        logger.info(f"[1/4] Processing {len(audio_paths)} audio files...")

        valid_audio_paths = [p for p in audio_paths if p.exists()]
        if not valid_audio_paths:
            raise ValueError("No valid audio files found")

        subtitle_entries = []
        current_time = 0.0
        audio_durations = []

        for i, audio_path in enumerate(valid_audio_paths):
            audio = AudioFileClip(str(audio_path))
            duration = audio.duration
            audio_durations.append(duration)

            if enable_captions and i < len(meta_data):
                line = meta_data[i].get("line", "")
                words = line.split()
                if words:
                    word_groups = []
                    for k in range(0, len(words), 2):
                        group = " ".join(words[k : k + 2])
                        word_groups.append(group)

                    time_per_group = duration / len(word_groups)
                    for j, group in enumerate(word_groups):
                        start = current_time + (j * time_per_group)
                        end = start + time_per_group
                        subtitle_entries.append(
                            {"start": start, "end": end, "text": group.upper()}
                        )

            current_time += duration
            audio.close()
            logger.info(f"  Audio {i + 1}/{len(valid_audio_paths)}: {duration:.1f}s")

        total_duration = sum(audio_durations)
        logger.info(f"  Total duration: {total_duration:.1f}s")

        logger.info("[2/4] Merging audio...")
        merged_audio_path = self.temp_dir / f"{project_id}_merged.mp3"
        self._merge_audio_ffmpeg(valid_audio_paths, merged_audio_path)

        if bg_music_path and bg_music_path.exists():
            logger.info("  Adding background music...")
            final_audio_path = self.temp_dir / f"{project_id}_final_audio.mp3"
            self._mix_audio_with_music(
                merged_audio_path,
                bg_music_path,
                final_audio_path,
                music_volume,
                total_duration,
            )
            merged_audio_path.unlink()
            merged_audio_path = final_audio_path

        logger.info("[3/4] Creating video with FFmpeg...")
        temp_video_path = self.temp_dir / f"{project_id}_temp.mp4"

        if bg_video_path and bg_video_path.exists():
            self._create_video_with_bg_ffmpeg(
                bg_video_path, merged_audio_path, temp_video_path, total_duration
            )
        else:
            self._create_solid_video_ffmpeg(
                merged_audio_path, temp_video_path, total_duration
            )

        if enable_captions and subtitle_entries:
            logger.info("[4/4] Burning subtitles...")
            ass_path = self.temp_dir / f"{project_id}.ass"
            self._generate_ass_subtitles(subtitle_entries, ass_path)
            self._burn_subtitles_ffmpeg(temp_video_path, ass_path, output_path)
            temp_video_path.unlink()
            ass_path.unlink()
        else:
            logger.info("[4/4] No subtitles, finalizing...")
            shutil.move(str(temp_video_path), str(output_path))

        if merged_audio_path.exists():
            merged_audio_path.unlink()

        elapsed = time.time() - start_time
        logger.info(f"Video created in {elapsed:.1f}s: {output_path}")

    def _merge_audio_ffmpeg(self, audio_paths: List[Path], output_path: Path) -> None:
        """Merge multiple audio files using FFmpeg filter_complex."""
        if len(audio_paths) == 1:
            shutil.copy(audio_paths[0], output_path)
            return

        input_args = []
        for path in audio_paths:
            input_args.extend(["-i", str(path)])

        filter_parts = "".join([f"[{i}:a]" for i in range(len(audio_paths))])
        filter_str = f"{filter_parts}concat=n={len(audio_paths)}:v=0:a=1[out]"

        cmd = (
            ["ffmpeg", "-y"]
            + input_args
            + ["-filter_complex", filter_str, "-map", "[out]", str(output_path)]
        )

        logger.info(f"  Merging {len(audio_paths)} audio files...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Audio merge failed: {result.stderr}")
            raise RuntimeError("Failed to merge audio files")

    def _mix_audio_with_music(
        self,
        voice_path: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float,
        duration: float,
    ) -> None:
        """Mix voice audio with background music."""
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
            "-filter_complex",
            f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first[out]",
            "-map",
            "[out]",
            "-t",
            str(duration),
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"Music mixing failed, using voice only")
            shutil.copy(voice_path, output_path)

    def _create_solid_video_ffmpeg(
        self, audio_path: Path, output_path: Path, duration: float
    ) -> None:
        """Create video with solid color background."""
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0f0f19:s={WIDTH}x{HEIGHT}:d={duration}:r=24",
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Video creation failed: {result.stderr}")
            raise RuntimeError("Failed to create video")

    def _create_video_with_bg_ffmpeg(
        self, bg_video_path: Path, audio_path: Path, output_path: Path, duration: float
    ) -> None:
        """Create video with looping background video."""
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(bg_video_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}[v]",
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-t",
            str(duration),
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Video creation failed: {result.stderr}")
            raise RuntimeError("Failed to create video with background")

    def _generate_ass_subtitles(self, entries: List[dict], output_path: Path) -> None:
        """Generate ASS subtitle file."""
        ass_content = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,0,5,10,10,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for entry in entries:
            start_time = self._seconds_to_ass_time(entry["start"])
            end_time = self._seconds_to_ass_time(entry["end"])
            text = (
                entry["text"]
                .replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
            )
            ass_content += (
                f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
            )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _burn_subtitles_ffmpeg(
        self, input_path: Path, ass_path: Path, output_path: Path
    ) -> None:
        """Burn ASS subtitles into video."""
        ass_path_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg",
            "-y",
            "-hwaccel",
            "auto",
            "-i",
            str(input_path),
            "-vf",
            f"ass='{ass_path_escaped}'",
            "-c:a",
            "copy",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-threads",
            "0",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"Subtitle burning failed")
            shutil.copy(input_path, output_path)


# Singleton instance
vertical_video_service = VerticalVideoService()
