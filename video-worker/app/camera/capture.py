import cv2
import logging
import time

from app.camera.video_source import VideoSource

logger = logging.getLogger(__name__)


class FrameCapture:
    def __init__(
        self,
        video_source: VideoSource,
        fps_limit: int,
        jpeg_quality: int
    ):
        self.video_source = video_source
        self.frame_interval = 1 / fps_limit
        self.jpeg_quality = jpeg_quality

    def frames(self):
        last_frame_time = 0

        while True:
            current_time = time.perf_counter()
            wait_time = self.frame_interval - (current_time - last_frame_time)
            if wait_time > 0:
                time.sleep(wait_time)

            success, frame = self.video_source.read_latest()
            if not success:
                logger.error("Captura encerrada porque nao foi possivel ler um frame")
                break

            last_frame_time = time.perf_counter()

            # Encode the frame as JPEG.
            success, encoded = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            )

            # Check whether encoding was successful.
            if not success:
                logger.warning("Nao foi possivel codificar o frame como JPEG")
                continue

            # Return the JPEG image as bytes.
            yield encoded.tobytes()