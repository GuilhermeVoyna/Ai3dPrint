import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


class LiveHub:
    def __init__(self):
        self.latest_frame_id = 0
        self.frames_processed = 0
        self._subscribers = set()

    async def publish(self, frame_id: int, frame: bytes, result: dict):
        self.latest_frame_id = frame_id
        self.frames_processed += 1
        packet = {
            "frame_id": frame_id,
            "frames_processed": self.frames_processed,
            "result": result,
            "frame": frame,
        }
        for queue in tuple(self._subscribers):
            self._put_latest(queue, packet)

    @staticmethod
    def _put_latest(queue: asyncio.Queue, value):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(value)

    def subscribe(self):
        queue = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self._subscribers.discard(queue)


def create_app(hub: LiveHub):
    app = FastAPI(title="Test3D Video Stream")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "alive", "service": "video-worker"}

    @app.websocket("/ws/live")
    async def live(websocket: WebSocket):
        await websocket.accept()
        queue = hub.subscribe()
        try:
            while True:
                packet = await queue.get()
                await websocket.send_text(json.dumps({
                    "frame_id": packet["frame_id"],
                    "frames_processed": packet["frames_processed"],
                    "result": packet["result"],
                }))
                await websocket.send_bytes(packet["frame"])
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            hub.unsubscribe(queue)

    return app
