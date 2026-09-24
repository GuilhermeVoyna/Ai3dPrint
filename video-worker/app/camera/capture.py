import cv2
import logging
import time

from app.camera.video_source import VideoSource


logger = logging.getLogger(__name__)


class FrameCapture:
    def __init__(
        self,
        video_source: VideoSource,
        jpeg_quality: int,
    ):
        self.video_source = video_source
        self.jpeg_quality = jpeg_quality

    def frames(self):
        while True:
            # ---------------------------------------------------------
            # Leitura do frame
            # ---------------------------------------------------------
            read_start = time.perf_counter()

            success, frame = self.video_source.read_latest()

            read_time = time.perf_counter() - read_start

            if not success:
                logger.error(
                    "Captura encerrada porque nao foi "
                    "possivel ler um frame"
                )
                break

            # ---------------------------------------------------------
            # Codificação JPEG
            # ---------------------------------------------------------
            encode_start = time.perf_counter()

            success, encoded = cv2.imencode(
                ".jpg",
                frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    self.jpeg_quality,
                ],
            )

            encode_time = time.perf_counter() - encode_start

            if not success:
                logger.warning(
                    "Nao foi possivel codificar "
                    "o frame como JPEG"
                )
                continue

            # ---------------------------------------------------------
            # Diagnóstico
            # ---------------------------------------------------------
            total_time = read_time + encode_time

            if total_time > 0.1:
                logger.info(
                    "FrameCapture | "
                    "Read: %.2f ms | "
                    "JPEG: %.2f ms | "
                    "Total: %.2f ms",
                    read_time * 1000,
                    encode_time * 1000,
                    total_time * 1000,
                )

            yield encoded.tobytes()