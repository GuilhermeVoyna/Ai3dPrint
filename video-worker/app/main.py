import asyncio
import logging
import time

import uvicorn

from app.config import (
    YOLO_WORKER_URL,
    VIDEO_SOURCE,
    WEBCAM_INDEX,
    FPS_LIMIT,
    JPEG_QUALITY,
    HOST,
    PORT,
)

from app.camera.video_source import VideoSource
from app.camera.capture import FrameCapture
from app.services.yolo_client import YoloClient
from app.stream_api import LiveHub, create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def video_pipeline(hub: LiveHub):
    logger.info("Iniciando video worker")
    logger.info("Fonte de video: %s", VIDEO_SOURCE)
    logger.info("Worker YOLO: %s", YOLO_WORKER_URL)

    source = VideoSource(VIDEO_SOURCE, webcam_index=WEBCAM_INDEX)
    logger.info("Abrindo fonte de video")
    source.open()
    logger.info("Fonte de video aberta")

    capture = FrameCapture(
        video_source=source,
        fps_limit=int(FPS_LIMIT),
        jpeg_quality=JPEG_QUALITY
    )

    yolo_client = YoloClient(YOLO_WORKER_URL)
    try:
        logger.info("Conectando ao worker YOLO")
        await yolo_client.connect()
        logger.info("Conectado ao worker YOLO")

        frames_sent = 0
        frame_iterator = iter(capture.frames())
        while True:
            frame = await asyncio.to_thread(next, frame_iterator, None)
            if frame is None:
                logger.error("Captura de video encerrada")
                break

            inference_started = time.perf_counter()
            resultado = await yolo_client.send_frame(frame)
            inference_seconds = time.perf_counter() - inference_started
            frames_sent += 1
            await hub.publish(frames_sent, frame, resultado)

            if frames_sent == 1 or frames_sent % 30 == 0:
                logger.info(
                    "Frames enviados ao YOLO: %d | inference_time=%.3fs | effective_fps=%.2f | Ultimo resultado: %s",
                    frames_sent,
                    inference_seconds,
                    1 / inference_seconds if inference_seconds else 0,
                    resultado
                )

    finally:
        logger.info("Encerrando video worker")
        await yolo_client.close()
        source.release()
        logger.info("Video worker encerrado")


async def dashboard_server(hub: LiveHub):
    config = uvicorn.Config(
        create_app(hub),
        host=HOST,
        port=PORT,
        log_level="info",
    )
    await uvicorn.Server(config).serve()


async def main():
    hub = LiveHub()
    if VIDEO_SOURCE.lower() in {"browser", "webcam-windows"}:
        yolo_client = YoloClient(YOLO_WORKER_URL)
        await yolo_client.connect()
        app = create_app(
            hub,
            yolo_client=yolo_client,
            source_mode="browser",
        )
        config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
        await uvicorn.Server(config).serve()
        return

    await asyncio.gather(
        video_pipeline(hub),
        dashboard_server(hub),
    )


if __name__ == "__main__":
    asyncio.run(main())