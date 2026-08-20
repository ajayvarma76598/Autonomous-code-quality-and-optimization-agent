import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.api.auth import require_role
from backend.workflows.router import workflow_router

router = APIRouter(prefix="/escalation", tags=["Escalation"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop = None

    async def connect(self, websocket: WebSocket):
        import asyncio

        self.loop = asyncio.get_running_loop()
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Manager connected to Escalation WebSocket.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Manager disconnected from Escalation WebSocket.")

    async def _broadcast_task(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")

    def safe_broadcast(self, message: dict):
        if self.loop and self.active_connections:
            import asyncio

            try:
                current_loop = asyncio.get_running_loop()
                if current_loop is self.loop:
                    self.loop.create_task(self._broadcast_task(message))
                    return
            except RuntimeError:
                pass
            asyncio.run_coroutine_threadsafe(self._broadcast_task(message), self.loop)

    async def broadcast(self, message: dict):
        await self._broadcast_task(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep the connection open to send escalations
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


pending_escalations: dict[str, dict] = {}


class ResolutionRequest(BaseModel):
    session_id: str
    action: str  # "APPROVE" or "REJECT"
    feedback: str = ""


@router.get("/pending", dependencies=[Depends(require_role(["admin"]))])
async def get_pending_escalations():
    """Returns active escalations that haven't been resolved."""
    return sorted(
        pending_escalations.values(), key=lambda x: x.get("timestamp", 0), reverse=True
    )


@router.post("/resolve", dependencies=[Depends(require_role(["admin"]))])
async def resolve_escalation(req: ResolutionRequest):
    """
    Called by the Manager Dashboard to resolve an interrupted workflow.
    """
    config = {"configurable": {"thread_id": req.session_id}}

    # Get current state
    try:
        current_state = workflow_router.workflow.get_state(config)
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Session not found or not active: {e}"
        )

    if not current_state or not current_state.next:
        raise HTTPException(
            status_code=400, detail="No active escalation found for this session."
        )

    # Update state based on action
    state_updates = {"workflow": {"requires_escalation": False, "status": "COMPLETE"}}
    if req.action == "REJECT":
        msg = "We do not have enough information to process this request."
        if req.feedback and req.feedback != "Resolved by manager.":
            msg += f" Manager note: {req.feedback}"
        state_updates["final_response"] = msg
    else:
        # If approved, we could leave it as is or append a note
        if req.feedback:
            existing_response = current_state.values.get("final_response") or ""
            state_updates["final_response"] = (
                existing_response + f"\n\n(Approved with note: {req.feedback})"
            )

    try:
        # Update state as if human_validation ran
        workflow_router.workflow.update_state(
            config, state_updates, as_node="human_validation"
        )

        if req.session_id in pending_escalations:
            del pending_escalations[req.session_id]

        return {"status": "success", "message": f"Escalation resolved: {req.action}"}
    except Exception as e:
        logger.error(f"Error resolving escalation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def trigger_escalation_alert(session_id: str, query: str, reasoning: str, verdict: str):
    """
    Helper function to broadcast to the manager dashboard.
    """
    payload = {
        "type": "ESCALATION",
        "session_id": session_id,
        "query": query,
        "reasoning": reasoning,
        "verdict": verdict,
        "timestamp": __import__("time").time(),
    }
    pending_escalations[session_id] = payload
    manager.safe_broadcast(payload)
