import asyncio
import logging

import uvicorn

from app.config import (
    YOLO_WORKER_URL,
    VIDEO_SOURCE,
    FPS_LIMIT,
    JPEG_QUALITY
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

    source = VideoSource(VIDEO_SOURCE)
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

            resultado = await yolo_client.send_frame(frame)
            frames_sent += 1
            await hub.publish(frames_sent, frame, resultado)

            if frames_sent == 1 or frames_sent % 30 == 0:
                logger.info(
                    "Frames enviados ao YOLO: %d | Ultimo resultado: %s",
                    frames_sent,
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
        host="0.0.0.0",
        port=8010,
        log_level="info",
    )
    await uvicorn.Server(config).serve()


async def main():
    hub = LiveHub()
    await asyncio.gather(
        video_pipeline(hub),
        dashboard_server(hub),
    )


if __name__ == "__main__":
    asyncio.run(main())