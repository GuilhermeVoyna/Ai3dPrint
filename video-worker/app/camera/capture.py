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
        self.fps_limit = 1 / fps_limit
        self.jpeg_quality = jpeg_quality

    def frames(self):
        last_frame_time = 0

        while True:
            success, frame = self.video_source.read()

            # Stop the loop if frame capture fails.
            if not success:
                logger.error("Captura encerrada porque nao foi possivel ler um frame")
                break

            current_time = time.perf_counter()

            # Check whether the frame interval has elapsed.
            if current_time - last_frame_time < self.fps_limit:
                continue

            # Update the time of the last processed frame.
            last_frame_time = current_time

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