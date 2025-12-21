"""
ImageGenerator Node - Generates images for each scene using Flux Schnell.
"""

import json
from typing import Dict, Any, List
from uuid import uuid4

from app.graph.state import GraphState
from app.services.image_service import image_service
from app.services.groq_service import groq_service
from app.models import ProjectStatus
from app.database import get_session_context
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def image_generator_node(state: GraphState) -> GraphState:
    """
    Generate images for scenes based on image_mode.

    Modes:
    - per_scene: Generate N images based on scenes_per_image ratio
    - single: Generate 1 image for entire video from story summary
    - upload: Use user-uploaded background image
    - none: Skip image generation (use solid backgrounds)

    Updates:
    - image_files: List of paths to generated images
    - image_prompts: List of prompts used
    - image_scene_indices: Mapping of which image to use for each scene
    - progress: Incremented to 0.25 on completion
    """
    logger.info("ImageGenerator node started", project_id=state["project_id"])

    state["current_step"] = "generating_images"
    image_mode = state.get("image_mode", "per_scene")

    try:
        # Update project status
        async with get_session_context() as session:
            from app.models import Project
            from uuid import UUID as UUIDType

            project = await session.get(Project, UUIDType(state["project_id"]))
            if project:
                project.status = ProjectStatus.GENERATING_IMAGES
                session.add(project)
            await session.commit()

        script_json = state["script_json"]
        scenes = script_json.get("scenes", [])
        num_scenes = len(scenes)

        logger.info(
            "Image generation config",
            project_id=state["project_id"],
            image_mode=image_mode,
            total_scenes=num_scenes,
        )

        if image_mode == "none":
            # Skip image generation - use solid backgrounds
            state["image_files"] = []
            state["image_scene_indices"] = []
            state["image_prompts"] = []
            logger.info(
                "Skipping image generation (mode=none)", project_id=state["project_id"]
            )

        elif image_mode == "upload":
            # Use user-uploaded background image
            background_url = state.get("background_image_url")
            if background_url:
                state["image_files"] = [background_url]
                # All scenes use the same image (index 0)
                state["image_scene_indices"] = [0] * num_scenes
                state["image_prompts"] = ["User-uploaded background"]
                logger.info(
                    "Using uploaded background",
                    project_id=state["project_id"],
                    url=background_url,
                )
            else:
                state["image_files"] = []
                state["image_scene_indices"] = []
                state["image_prompts"] = []
                logger.warning(
                    "Upload mode but no background_image_url provided",
                    project_id=state["project_id"],
                )

        elif image_mode == "single":
            # Generate single image for entire story
            story_summary = await _generate_story_summary(script_json)
            image_prompts = [story_summary]

            image_files = await image_service.generate_batch(
                project_id=state["project_id"], prompts=image_prompts
            )

            valid_images = [p for p in image_files if p is not None]
            if valid_images:
                state["image_files"] = valid_images
                # All scenes use the same image (index 0)
                state["image_scene_indices"] = [0] * num_scenes
                state["image_prompts"] = image_prompts
            else:
                state["image_files"] = []
                state["image_scene_indices"] = []
                state["image_prompts"] = []

            logger.info("Generated single story image", project_id=state["project_id"])

        else:  # per_scene (default)
            scenes_per_image = state.get("scenes_per_image", 2)

            # Group scenes for prompt generation
            scene_groups = []
            for i in range(0, num_scenes, scenes_per_image):
                group = scenes[i : i + scenes_per_image]
                scene_groups.append(group)

            # Generate image prompts using LLM (one per group)
            image_prompts = await _generate_image_prompts_for_groups(scene_groups)

            logger.info(
                "Generated image prompts",
                project_id=state["project_id"],
                count=len(image_prompts),
            )

            # Generate images
            image_files = await image_service.generate_batch(
                project_id=state["project_id"], prompts=image_prompts
            )

            # Build scene-to-image mapping
            valid_images = [p for p in image_files if p is not None]
            image_for_scene = []

            # Map each scene to its corresponding image index
            for scene_idx in range(num_scenes):
                image_idx = scene_idx // scenes_per_image
                if image_idx < len(valid_images):
                    image_for_scene.append(image_idx)
                else:
                    image_for_scene.append(-1)

            state["image_files"] = valid_images
            state["image_scene_indices"] = image_for_scene
            state["image_prompts"] = image_prompts

            logger.info(
                "Image generation completed",
                project_id=state["project_id"],
                images_generated=len(valid_images),
                total_scenes=num_scenes,
            )

        state["progress"] = 0.25

        # Update project status
        async with get_session_context() as session:
            from app.models import Project
            from uuid import UUID as UUIDType

            project = await session.get(Project, UUIDType(state["project_id"]))
            if project:
                project.status = ProjectStatus.GENERATING_AUDIO
                session.add(project)
            await session.commit()

    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(error_msg, project_id=state["project_id"])
        state["errors"].append(error_msg)

        # Use empty list - video composer will use solid backgrounds
        state["image_files"] = []
        state["image_scene_indices"] = []
        state["image_prompts"] = []

    return state


async def _generate_story_summary(script_json: Dict[str, Any]) -> str:
    """Generate a single image prompt from the entire script story."""
    title = script_json.get("title", "")
    scenes = script_json.get("scenes", [])

    # Build story context
    all_lines = []
    for scene in scenes[:5]:  # Use first 5 scenes for summary
        speaker = scene.get("speaker", "")
        line = scene.get("line", "")
        all_lines.append(f"{speaker}: {line}")

    prompt = f"""You are an expert at creating image prompts for AI image generators.

Given this video script, generate ONE image prompt that captures the overall theme and mood.
The image will be used as a background for the entire video.

Title: {title}
Script excerpt:
{chr(10).join(all_lines)}

Requirements:
1. Create a visually stunning, cinematic background
2. Capture the overall theme and mood of the story
3. Use descriptive style keywords (cinematic, 4K, dramatic lighting, etc.)
4. Keep the prompt under 100 words

Respond with ONLY the image prompt, no quotes or explanation."""

    try:
        response = await groq_service.generate_raw(prompt)
        return response.strip()
    except Exception as e:
        logger.error(f"Failed to generate story summary: {e}")
        return "Cinematic abstract background, dramatic lighting, 4K quality, professional video background"


async def _generate_image_prompts_for_groups(
    scene_groups: List[List[Dict[str, Any]]],
) -> List[str]:
    """
    Use LLM to generate image prompts from grouped scenes.
    Each group of scenes gets one image prompt.
    """
    # Build group summaries
    group_texts = []
    for i, group in enumerate(scene_groups):
        scenes_in_group = []
        for scene in group:
            speaker = scene.get("speaker", "Unknown")
            line = scene.get("line", "")
            scenes_in_group.append(f'{speaker}: "{line}"')
        group_texts.append(f"Group {i + 1}:\n" + "\n".join(scenes_in_group))

    prompt = f"""You are an expert at creating image prompts for AI image generators.

Given these grouped video script scenes, generate ONE image prompt per group. The images will be used as backgrounds for a faceless YouTube video.
Requirements:
1. Create visually interesting, relevant backgrounds that capture the essence of ALL scenes in the group
2. Focus on a common visual theme that works for the entire group
3. Use descriptive style keywords (cinematic, 4K, dramatic lighting, etc.)
4. Keep each prompt under 100 words

SCENE GROUPS:
{chr(10).join(group_texts)}

Respond with ONLY a JSON array of strings (one prompt per group):
["prompt for group 1", "prompt for group 2", ...]
"""

    try:
        response = await groq_service.generate_raw(prompt)

        # Clean response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        prompts = json.loads(response)

        # Validate
        if not isinstance(prompts, list):
            raise ValueError("Expected list of prompts")

        # Ensure we have enough prompts
        while len(prompts) < len(scene_groups):
            prompts.append(
                "Abstract colorful background, cinematic lightning, 4k quality"
            )

        return prompts[: len(scene_groups)]

    except Exception as e:
        logger.error(f"Failed to generate image prompts: {e}")
        # Fallback prompts
        return [
            "Abstract colorful gradient background, cinematic lighting, 4K quality"
            for _ in scene_groups
        ]


def should_continue_after_images(state: GraphState) -> str:
    """
    Conditional edge: Always continue to audio generation
    Images are optional - solid backgrounds are used as fallback.
    """
    return "audio_generator"
