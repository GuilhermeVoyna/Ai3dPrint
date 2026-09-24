import logging
import time

logger = logging.getLogger(__name__)


class FailureConfirmationWorker:
    def __init__(
        self,
        moonraker_client,
        threshold: float,
        mode: str,
        confirmation_frames: int,
        confirmation_time_seconds: float,
        clock=time.monotonic,
    ):
        if mode not in {"frames", "time"}:
            raise ValueError("FAILURE_CONFIRMATION_MODE must be 'frames' or 'time'")
        self.moonraker = moonraker_client
        self.threshold = threshold
        self.mode = mode
        self.confirmation_frames = confirmation_frames
        self.confirmation_time_seconds = confirmation_time_seconds
        self.clock = clock
        self.consecutive_frames = 0
        self.started_at = None
        self.pause_sent = False

    @staticmethod
    def _max_confidence(result: dict) -> float:
        detections = result.get("detections", []) if isinstance(result, dict) else []
        return max(
            (float(item.get("confidence", 0.0)) for item in detections),
            default=0.0,
        )

    def _reset(self, confidence: float) -> None:
        self.consecutive_frames = 0
        self.started_at = None

    def _confirmed(self) -> bool:
        if self.mode == "frames":
            return self.consecutive_frames >= self.confirmation_frames
        return self.started_at is not None and (
            self.clock() - self.started_at >= self.confirmation_time_seconds
        )

    async def process(self, packet: dict) -> None:
        frame_id = packet.get("frame_id") if isinstance(packet, dict) else None
        result = packet.get("result", packet) if isinstance(packet, dict) else {}
        detections = result.get("detections", []) if isinstance(result, dict) else []
        confidence = self._max_confidence(result)

        if confidence < self.threshold:
            self._reset(confidence)
            return

        logger.warning(
            "Suspicious frame detected: frame=%s | confidence=%.2f | threshold=%.2f",
            frame_id, confidence, self.threshold,
        )

        if self.pause_sent:
            return
        if self.started_at is None:
            self.started_at = self.clock()
        self.consecutive_frames += 1
        if not self._confirmed():
            return
        state = await self.moonraker.safe_get_print_state()
        if state == "paused":
            logger.warning(
                "Pause not sent: printer is already paused | frame=%s",
                frame_id,
            )
            self.pause_sent = True
            return
        if state != "printing":
            self._reset(confidence)
            return
        self.pause_sent = await self.moonraker.safe_pause_print()
