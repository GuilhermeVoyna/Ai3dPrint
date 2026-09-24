import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


class LiveHub:
    def __init__(self):
        self.latest_frame_id = 0
        self.frames_processed = 0
        self._subscribers = set()
        self._result_subscribers = set()

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
        result_packet = {
            "frame_id": frame_id,
            "frames_processed": self.frames_processed,
            "result": result,
        }
        for queue in tuple(self._result_subscribers):
            self._put_latest(queue, result_packet)

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

    def subscribe_results(self):
        queue = asyncio.Queue(maxsize=1)
        self._result_subscribers.add(queue)
        return queue

    def unsubscribe_results(self, queue):
        self._result_subscribers.discard(queue)


def create_app(hub: LiveHub, yolo_client=None, source_mode: str = ""):
    app = FastAPI(title="Test3D Video Stream")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {
            "status": "alive",
            "service": "video-worker",
            "video_source": source_mode,
        }

    @app.websocket("/ws/input")
    async def input_stream(websocket: WebSocket):
        if yolo_client is None:
            await websocket.close(code=1008, reason="Browser input is disabled")
            return

        await websocket.accept()
        try:
            while True:
                frame = await websocket.receive_bytes()
                result = await yolo_client.send_frame(frame)
                await hub.publish(hub.frames_processed + 1, frame, result)
                await websocket.send_text(json.dumps(result))
        except (WebSocketDisconnect, RuntimeError):
            pass

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

    @app.websocket("/ws/detections")
    async def detections(websocket: WebSocket):
        await websocket.accept()
        queue = hub.subscribe_results()
        try:
            while True:
                await websocket.send_text(json.dumps(await queue.get()))
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            hub.unsubscribe_results(queue)

    return app
