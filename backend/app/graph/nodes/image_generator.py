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
    Generate images for scenes in the script based on scenes_per_image ratio.

    Uses LLM to create image prompts from scene context,
    then generates images using SDXL.

    If scenes_per_image=2, generates 1 image for every 2 scenes.

    Updates:
    - image_files: List of paths to generated images
    - image_prompts: List of prompts used
    - image_scene_indices: Mapping of which image to use for each scene
    - progress: Incremented to 0.25 on completion
    """
    logger.info("ImageGenerator node started", project_id=state["project_id"])

    state["current_step"] = "generating_images"

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
        scenes_per_image = state.get("scenes_per_image", 2)

        # Calculate how many images we need
        num_images = max(1, (len(scenes) + scenes_per_image - 1) // scenes_per_image)

        logger.info(
            "Image generation config",
            project_id=state["project_id"],
            total_scenes=len(scenes),
            scenes_per_image=scenes_per_image,
            images_to_generate=num_images,
        )

        # Group scenes for prompt generation
        scene_groups = []
        for i in range(0, len(scenes), scenes_per_image):
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
        # For scenes_per_image=2: scenes 0,1 use image 0; scenes 2,3 use image 1, etc.
        valid_images = []
        image_for_scene = []  # Index of which image to use for each scene

        for i, path in enumerate(image_files):
            if path is not None:
                valid_images.append(path)

        # Map each scene to its corresponding image index
        for scene_idx in range(len(scenes)):
            image_idx = scene_idx // scenes_per_image
            # Use the valid image index, or -1 if no image
            if image_idx < len(valid_images):
                image_for_scene.append(image_idx)
            else:
                image_for_scene.append(-1)

        state["image_files"] = valid_images
        state["image_scene_indices"] = image_for_scene
        state["image_prompts"] = image_prompts
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

        logger.info(
            "Image generation completed",
            project_id=state["project_id"],
            images_generated=len(valid_images),
            total_scenes=len(scenes),
        )

    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(error_msg, project_id=state["project_id"])
        state["errors"].append(error_msg)

        # Use empty list - video composer will use solid backgrounds
        state["image_files"] = []
        state["image_scene_indices"] = []
        state["image_prompts"] = []

    return state


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
