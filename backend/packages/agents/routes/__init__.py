from fastapi import APIRouter, WebSocket, Depends
from .conversations import router as conversations_router
from .tools import router as tools_router
from .websocket import websocket_chat_endpoint
from packages.auth.dependencies import get_current_active_user

# Create main agents router
router = APIRouter(prefix="/agents", tags=["agents"])

# Include sub-routers with auth dependency at router level
router.include_router(
    conversations_router, dependencies=[Depends(get_current_active_user)]
)
router.include_router(tools_router, dependencies=[Depends(get_current_active_user)])


# Add WebSocket route - auth handled internally via token query param
@router.websocket("/conversations/{conversation_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket, conversation_id: int, token: str = None
):
    """WebSocket endpoint for real-time agent chat.

    Note: Authentication is handled internally via token query parameter,
    not via standard dependency injection since WebSockets require special handling.
    """
    await websocket_chat_endpoint(websocket, conversation_id, token)
