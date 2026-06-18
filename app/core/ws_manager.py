import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active:
            self.active[user_id] = []
        self.active[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active:
            self.active[user_id] = [ws for ws in self.active[user_id] if ws is not websocket]
            if not self.active[user_id]:
                del self.active[user_id]

    async def send_to_user(self, user_id: int, data: dict):
        for ws in self.active.get(user_id, []):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

    async def broadcast_to_users(self, user_ids: list[int], data: dict):
        for uid in user_ids:
            await self.send_to_user(uid, data)


manager = ConnectionManager()
