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
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def video_pipeline(hub: LiveHub):
    logger.info("Iniciando video worker")
    logger.info("Fonte de video: %s", VIDEO_SOURCE)
    logger.info("Worker YOLO: %s", YOLO_WORKER_URL)

    source = VideoSource(
        VIDEO_SOURCE,
        webcam_index=WEBCAM_INDEX,
    )

    logger.info("Abrindo fonte de video")
    source.open()
    logger.info("Fonte de video aberta")

    capture = FrameCapture(
        video_source=source,
        jpeg_quality=JPEG_QUALITY,
    )

    yolo_client = YoloClient(YOLO_WORKER_URL)

    try:
        logger.info("Conectando ao worker YOLO")

        await yolo_client.connect()

        logger.info("Conectado ao worker YOLO")

        frames_sent = 0

        frame_iterator = iter(capture.frames())

        while True:
            # ---------------------------------------------------------
            # CAPTURE
            # ---------------------------------------------------------
            capture_start = time.perf_counter()

            frame = await asyncio.to_thread(
                next,
                frame_iterator,
                None,
            )

            capture_time = time.perf_counter() - capture_start

            if frame is None:
                logger.error("Captura de video encerrada")
                break

            # ---------------------------------------------------------
            # YOLO
            # ---------------------------------------------------------
            yolo_start = time.perf_counter()

            resultado = await yolo_client.send_frame(frame)

            yolo_time = time.perf_counter() - yolo_start

            # ---------------------------------------------------------
            # PUBLISH
            # ---------------------------------------------------------
            frames_sent += 1

            publish_start = time.perf_counter()

            await hub.publish(
                frames_sent,
                frame,
                resultado,
            )

            publish_time = time.perf_counter() - publish_start

            # ---------------------------------------------------------
            # TOTAL
            # ---------------------------------------------------------
            total_time = (
                capture_time
                + yolo_time
                + publish_time
            )

            # ---------------------------------------------------------
            # LOG
            # ---------------------------------------------------------
            if frames_sent == 1 or frames_sent % 30 == 0:
                capture_ms = capture_time * 1000
                yolo_ms = yolo_time * 1000
                publish_ms = publish_time * 1000
                total_ms = total_time * 1000

                pipeline_fps = (
                    1.0 / total_time
                    if total_time > 0
                    else 0.0
                )

                yolo_fps = (
                    1.0 / yolo_time
                    if yolo_time > 0
                    else 0.0
                )

                logger.info(
                    "Frames: %d | "
                    "Capture: %.2f ms | "
                    "YOLO: %.2f ms | "
                    "Publish: %.2f ms | "
                    "Pipeline: %.2f ms | "
                    "YOLO FPS: %.2f | "
                    "Pipeline FPS: %.2f | "
                    "Target FPS: %.1f",
                    frames_sent,
                    capture_ms,
                    yolo_ms,
                    publish_ms,
                    total_ms,
                    yolo_fps,
                    pipeline_fps,
                    float(FPS_LIMIT),
                )

    except Exception:
        logger.exception("Erro no video pipeline")
        raise

    finally:
        logger.info("Encerrando video worker")

        try:
            await yolo_client.close()
        except Exception:
            logger.exception("Erro ao fechar conexão com YOLO")

        try:
            source.release()
        except Exception:
            logger.exception("Erro ao liberar fonte de video")

        logger.info("Video worker encerrado")


async def dashboard_server(hub: LiveHub):
    config = uvicorn.Config(
        create_app(hub),
        host=HOST,
        port=PORT,
        log_level="info",
    )

    server = uvicorn.Server(config)

    await server.serve()


async def main():
    hub = LiveHub()

    await asyncio.gather(
        video_pipeline(hub),
        dashboard_server(hub),
    )


if __name__ == "__main__":
    asyncio.run(main())