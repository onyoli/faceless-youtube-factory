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

    state["current_step"] = "generting images"

    pass