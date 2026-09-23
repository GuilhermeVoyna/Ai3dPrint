import cv2
import logging


logger = logging.getLogger(__name__)


class VideoSource:
    def __init__(self, source):
        self.source = source
        self.camera = None

    def open(self):
        logger.info("Conectando a fonte de video: %s", self.source)
        self.camera = cv2.VideoCapture(self.source)

        if not self.camera.isOpened():
            logger.error("Nao foi possivel abrir a fonte de video: %s", self.source)
            raise RuntimeError(
                f"Não foi possível abrir a fonte: {self.source}"
        )

    def read(self):
        if self.camera is None:
            raise RuntimeError("A câmera não foi aberta.")

        success, frame = self.camera.read()
        if not success:
            logger.error("A fonte de video nao entregou um frame")

        return success, frame

    def release(self):
        if self.camera is not None:
            self.camera.release()
            logger.info("Fonte de video liberada")