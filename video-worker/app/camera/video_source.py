import cv2
import logging


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
        if normalized_source.lower() in {"webcam", "camera", "webcam-linux"}:
            return webcam_index

        if normalized_source.isdigit():
            return int(normalized_source)

        return normalized_source

    def open(self):
        logger.info("Conectando a fonte de video: %s", self.source)
        self.camera = cv2.VideoCapture(self.source)

        if not self.camera.isOpened():
            logger.error("Nao foi possivel abrir a fonte de video: %s", self.source)
            raise RuntimeError(
                f"Não foi possível abrir a fonte: {self.source}"
        )

        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read_latest(self, max_buffered_frames: int = 8):
        if self.camera is None:
            raise RuntimeError("A câmera não foi aberta.")

        success, frame = self.camera.read()
        if not success:
            logger.error("A fonte de video nao entregou um frame")
            return success, frame

        for _ in range(max_buffered_frames):
            if not self.camera.grab():
                break
            success, latest_frame = self.camera.retrieve()
            if not success:
                break
            frame = latest_frame

        return success, frame

    def read(self):
        return self.read_latest(max_buffered_frames=0)

    def release(self):
        if self.camera is not None:
            self.camera.release()
            logger.info("Fonte de video liberada")