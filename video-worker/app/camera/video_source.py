import cv2
import logging
import time


logger = logging.getLogger(__name__)


class VideoSource:
    def __init__(self, source, webcam_index: int = 0):
        self.source = self._normalize_source(source, webcam_index)
        self.camera = None

    @staticmethod
    def _normalize_source(source, webcam_index: int):
        if isinstance(source, int):
            return source

        normalized_source = str(source).strip()

        if normalized_source.lower() in {
            "webcam",
            "camera",
            "webcam-linux",
        }:
            return webcam_index

        if normalized_source.isdigit():
            return int(normalized_source)

        return normalized_source

    def open(self):
        logger.info(
            "Conectando a fonte de video: %s",
            self.source,
        )

        self.camera = cv2.VideoCapture(self.source)

        if not self.camera.isOpened():
            logger.error(
                "Nao foi possivel abrir a fonte de video: %s",
                self.source,
            )

            raise RuntimeError(
                f"Nao foi possivel abrir a fonte: {self.source}"
            )

        # Tenta manter o buffer pequeno.
        self.camera.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1,
        )

        logger.info("Fonte de video conectada")

    def read_latest(self):
        if self.camera is None:
            raise RuntimeError(
                "A câmera não foi aberta."
            )

        start = time.perf_counter()

        success, frame = self.camera.read()

        elapsed = time.perf_counter() - start

        if not success:
            logger.error(
                "A fonte de video nao entregou um frame"
            )

            return False, None

        # Log apenas quando a leitura estiver lenta.
        if elapsed > 0.05:
            logger.warning(
                "VideoSource.read() lento: %.2f ms",
                elapsed * 1000,
            )

        return True, frame

    def read(self):
        return self.read_latest()

    def release(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

            logger.info(
                "Fonte de video liberada"
            )