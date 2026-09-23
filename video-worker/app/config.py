import os

YOLO_WORKER_URL = os.getenv(
    "YOLO_WORKER_URL",
    "ws://localhost:8002/inference"
)

VIDEO_SOURCE = os.getenv(
    "VIDEO_SOURCE",
    "webcam-windows"
)
WEBCAM_INDEX = int(os.getenv("WEBCAM_INDEX", "0"))

FPS_LIMIT = int(os.getenv("FPS_LIMIT", "30"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8010"))