"""
websocket.py
A simple per-user WebSocket connection registry. Later phases (Phase 2+)
push live notifications, announcements, and assignment updates through
`manager.send_to_user(user_id, payload)`. A user can have more than one
open connection (multiple tabs/devices), so we keep a list per user_id.
"""

from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if websocket in self.active_connections.get(user_id, []):
            self.active_connections[user_id].remove(websocket)
        if not self.active_connections.get(user_id):
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(payload)

    async def broadcast(self, payload: dict):
        for connections in self.active_connections.values():
            for ws in connections:
                await ws.send_json(payload)


manager = ConnectionManager()
