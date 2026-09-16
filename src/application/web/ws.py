"""
WebSocket Connection Manager for real-time telemetry streaming.
"""

import json
from typing import Any
from fastapi import WebSocket
from application.utils.logging import get_logger

logger = get_logger("web.ws")


class WebSocketManager:
    """Manages active WebSocket client connections and broadcasts telemetry updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug("Client connected via WebSocket. Active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug("Client disconnected from WebSocket. Active: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast payload to all connected clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps(message, default=str)
        dead_connections: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.debug("Error sending to WS client: %s", e)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)
