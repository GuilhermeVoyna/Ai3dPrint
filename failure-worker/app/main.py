import asyncio
import json
import logging

import websockets

from app.config import (
    FAILURE_CONFIRMATION_FRAMES,
    FAILURE_CONFIRMATION_MODE,
    FAILURE_CONFIRMATION_TIME_SECONDS,
    FAILURE_CONFIDENCE_THRESHOLD,
    MOONRAKER_TIMEOUT_SECONDS,
    MOONRAKER_URL,
    VIDEO_RESULTS_URL,
)
from app.services.failure_confirmation import FailureConfirmationWorker
from app.services.moonraker_client import MoonrakerClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def monitor(worker: FailureConfirmationWorker):
    while True:
        try:
            async with websockets.connect(VIDEO_RESULTS_URL) as connection:
                async for payload in connection:
                    await worker.process(json.loads(payload))
        except asyncio.CancelledError:
            raise
        except (OSError, websockets.exceptions.WebSocketException, json.JSONDecodeError) as error:
            logger.error("Video results connection failed: %s", error)
            await asyncio.sleep(1)


async def main():
    moonraker = MoonrakerClient(MOONRAKER_URL, MOONRAKER_TIMEOUT_SECONDS)
    worker = FailureConfirmationWorker(
        moonraker,
        FAILURE_CONFIDENCE_THRESHOLD,
        FAILURE_CONFIRMATION_MODE,
        FAILURE_CONFIRMATION_FRAMES,
        FAILURE_CONFIRMATION_TIME_SECONDS,
    )
    await monitor(worker)


if __name__ == "__main__":
    asyncio.run(main())
