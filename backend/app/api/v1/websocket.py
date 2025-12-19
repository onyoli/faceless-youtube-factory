"""
WebSocket endpoint for real-time project status updates.
"""
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Store active WebSocket connections by project ID
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, project_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection for a project."""
        await websocket.accept()
        if project_id not in self.connections:
            self.connections[project_id] = set()
        self.connections[project_id].add(websocket)
        logger.info("WebSocket connected", project_id=project_id)
    
    def disconnect(self, project_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if project_id in self.connections:
            self.connections[project_id].discard(websocket)
            if not self.connections[project_id]:
                del self.connections[project_id]
        logger.info("WebSocket disconnected", project_id=project_id)
    
    async def send_to_project(self, project_id: str, message: dict):
        """Send a message to all connections for a project."""
        if project_id in self.connections:
            dead_connections = set()
            for websocket in self.connections[project_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    dead_connections.add(websocket)
            
            # Clean up dead connections
            for ws in dead_connections:
                self.connections[project_id].discard(ws)
    
    async def broadcast_status(self, project_id: str, status: str, progress: float):
        """Broadcast a status change to all project subscribers."""
        await self.send_to_project(project_id, {
            "type": "status_change",
            "status": status,
            "progress": progress
        })
    
    async def broadcast_error(self, project_id: str, message: str):
        """Broadcast an error to all project subscribers."""
        await self.send_to_project(project_id, {
            "type": "error",
            "message": message
        })
    
    async def broadcast_completed(self, project_id: str, video_url: str):
        """Broadcast completion to all project subscribers."""
        await self.send_to_project(project_id, {
            "type": "completed",
            "video_url": video_url
        })
    
    async def broadcast_published(self, project_id: str, youtube_url: str):
        """Broadcast YouTube publish to all project subscribers."""
        await self.send_to_project(project_id, {
            "type": "published",
            "youtube_url": youtube_url
        })


# Singleton connection manager
ws_manager = ConnectionManager()


@router.websocket("/ws/projects/{project_id}")
async def project_websocket(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time project updates.
    
    Clients connect here to receive status changes, errors, and completion events.
    """
    await ws_manager.connect(project_id, websocket)
    
    try:
        # Keep the connection open
        while True:
            # Wait for any message from client (ping/pong or close)
            data = await websocket.receive_text()
            
            # Echo back as heartbeat confirmation
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception as e:
        logger.error("WebSocket error", project_id=project_id, error=str(e))
        ws_manager.disconnect(project_id, websocket)
