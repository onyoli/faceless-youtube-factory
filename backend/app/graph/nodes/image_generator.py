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
    Generate images for each scene in the script.

    Uses LLM to create image prompts from scene context,
    then generates images using Flux Schnell.

    Updates:
    - image_files: List of paths to generated images
    - image_prompts: List of prompts used
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

        # Generate image prompts using LLM
        image_prompts = await _generate_image_prompts(scenes)

        logger.info(
            "Generated image prompts",
            project_id=state["project_id"],
            count=len(image_prompts),
        )

        # Generate images
        image_files = await image_service.generate_batch(
            project_id=state["project_id"], prompts=image_prompts
        )

        # Filter successful generations
        valid_images = []
        valid_indices = []
        for i, path in enumerate(image_files):
            if path is not None:
                valid_images.append(path)
                valid_indices.append(i)

        state["image_files"] = valid_images
        state["image_scene_indices"] = valid_indices
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
            successful=len(valid_images),
            total=len(scenes),
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


async def _generate_image_prompts(scenes: List[Dict[str, Any]]) -> List[str]:
    """
    Use LLM to generate image prompts from scene dialogue.
    """
    # Build scene summaries
    scene_texts = []
    for i, scene in enumerate(scenes):
        speaker = scene.get("speaker", "Unknown")
        line = scene.get("line", "")
        scene_texts.append(f'Scene {i + 1} - {speaker}: "{line}"')

    prompt = f"""You are an expert at creating image prompts for AI image generators.

Given these video script scenes, generate ONE image prompt per scene. The images will be used as backgrounds for a faceless YouTube video.
Requirements:
1. Create visually interesting, relevant backgrounds
2. Focus on what could the viewer imagine if they were in the scene
3. Use descriptive style keywords (cinematic, 4K, dramatic lighting, etc.)
4. Keep each prompt under 100 words

SCENES:
{chr(10).join(scene_texts)}

Respond with ONLY a JSON array of strings (one prompt per scene):
["prompt for scene 1", "prompt for scene 2", ...]
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
        while len(prompts) < len(scenes):
            prompts.append(
                "Abstract colorful background, cinematic lightning, 4k quality"
            )

        return prompts[: len(scenes)]

    except Exception as e:
        logger.error(f"Failed to generate image prompts: {e}")
        # Fallback prompts
        return [
            "Abstract colorful gradient background, cinematic lighting, 4K quality"
            for _ in scenes
        ]


def should_continue_after_images(state: GraphState) -> str:
    """
    Conditional edge: Always continue to audio generation
    Images are optional - solid backgrounds are used as fallback.
    """
    return "audio_generator"
