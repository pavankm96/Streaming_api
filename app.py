from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Change this for production security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

meetings = {}  # Store active meetings
active_connections = {}  # Track WebSocket connections per meeting


class MeetingCreate(BaseModel):
    host: str


@app.post("/create_meeting/")
async def create_meeting(meeting: MeetingCreate):
    meeting_id = str(uuid.uuid4())[:8]  # Generate an 8-character meeting ID
    meetings[meeting_id] = {"host": meeting.host, "participants": []}
    return {"meeting_id": meeting_id}


@app.websocket("/ws/{meeting_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, username: str):
    await websocket.accept()

    # Ensure the meeting exists
    if meeting_id not in meetings:
        await websocket.close(code=1008)  # Policy violation
        return

    # Register WebSocket connection
    if meeting_id not in active_connections:
        active_connections[meeting_id] = []
    
    if websocket not in active_connections[meeting_id]:
        active_connections[meeting_id].append(websocket)

    print(f"User {username} joined meeting {meeting_id}")

    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username}: {data}"
            print(f"Received: {message}")

            # Broadcast message to all participants
            for conn in active_connections[meeting_id]:
                try:
                    await conn.send_text(message)
                except Exception as e:
                    print(f"Error sending to {conn}: {e}")

    except WebSocketDisconnect:
        print(f"User {username} disconnected from {meeting_id}")

    finally:
        # Remove WebSocket from active connections
        if websocket in active_connections.get(meeting_id, []):
            active_connections[meeting_id].remove(websocket)

        # Remove empty meetings
        if not active_connections.get(meeting_id):
            del active_connections[meeting_id]
            print(f"Meeting {meeting_id} ended (No participants left).")


# Explicitly register WebSocket route
def register_routes():
    app.router.add_websocket_route("/ws/{meeting_id}/{username}", websocket_endpoint)

register_routes()
