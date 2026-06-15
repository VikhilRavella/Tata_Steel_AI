from fastapi import WebSocket
from typing import Dict, List
import asyncio, logging, json
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Supports personal messages and role-based broadcasts.
    Thread-safe with asyncio.Lock.
    """

    def __init__(self):
        self.active: Dict[int, WebSocket] = {}
        self.role_map: Dict[str, List[int]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, user_id: int, role: str):
        await ws.accept()
        async with self._lock:
            self.active[user_id] = ws
            self.role_map.setdefault(role, [])
            if user_id not in self.role_map[role]:
                self.role_map[role].append(user_id)
        logger.info(f'WS connected: user_id={user_id} role={role}')

    async def disconnect(self, user_id: int):
        async with self._lock:
            self.active.pop(user_id, None)
            for users in self.role_map.values():
                if user_id in users:
                    users.remove(user_id)
        logger.info(f'WS disconnected: user_id={user_id}')

    async def send_to_user(self, user_id: int, payload: dict) -> bool:
        ws = self.active.get(user_id)
        if not ws:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception as e:
            logger.error(f'WS send failed for user {user_id}: {e}')
            await self.disconnect(user_id)
            return False

    async def broadcast_to_role(self, role: str, payload: dict) -> int:
        user_ids = self.role_map.get(role, []).copy()
        results = await asyncio.gather(*[self.send_to_user(uid, payload) for uid in user_ids], return_exceptions=True)
        return sum((1 for r in results if r is True))

    async def broadcast_to_all(self, payload: dict):
        all_ids = list(self.active.keys())
        await asyncio.gather(*[self.send_to_user(uid, payload) for uid in all_ids], return_exceptions=True)
ws_manager = ConnectionManager()