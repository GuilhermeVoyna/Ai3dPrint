import asyncio
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class MoonrakerClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str) -> dict:
        if not self.base_url:
            raise RuntimeError("MOONRAKER_URL is not configured")
        request = Request(
            f"{self.base_url}{path}",
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Moonraker returned HTTP {response.status}")
            payload = response.read()
            return json.loads(payload) if payload else {}

    async def get_print_state(self) -> str:
        response = await asyncio.to_thread(
            self._request, "GET", "/printer/objects/query?print_stats"
        )
        try:
            return response["result"]["status"]["print_stats"]["state"]
        except (KeyError, TypeError) as error:
            raise RuntimeError("Moonraker response has no print_stats.state") from error

    async def pause_print(self) -> None:
        await asyncio.to_thread(self._request, "POST", "/printer/print/pause")

    async def safe_get_print_state(self):
        try:
            return await self.get_print_state()
        except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
            logger.error("Failed to read printer state from Moonraker: %s", error)
            return None

    async def safe_pause_print(self) -> bool:
        try:
            await self.pause_print()
            return True
        except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
            logger.error("Failed to pause printer via Moonraker: %s", error)
            return False
