import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.services.failure_confirmation import FailureConfirmationWorker
from app.services.moonraker_client import MoonrakerClient


class FakeMoonraker:
    def __init__(self, state="printing", pause_result=True):
        self.state = state
        self.pause_result = pause_result
        self.pause_calls = 0

    async def safe_get_print_state(self):
        return self.state

    async def safe_pause_print(self):
        self.pause_calls += 1
        if self.pause_result:
            self.state = "paused"
        return self.pause_result


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class FailureWorkerTests(unittest.TestCase):
    @staticmethod
    def result(confidence):
        return {"detections": [{"confidence": confidence}]}

    @staticmethod
    def run_async(coroutine):
        return asyncio.run(coroutine)

    def test_frames_threshold_confirmation_reset_and_idempotency(self):
        moonraker = FakeMoonraker()
        worker = FailureConfirmationWorker(moonraker, 0.60, "frames", 3, 5)
        self.run_async(worker.process({"frame_id": 1, "result": self.result(0.59)}))
        self.run_async(worker.process({"frame_id": 2, "result": self.result(0.60)}))
        self.run_async(worker.process({"frame_id": 3, "result": self.result(0.80)}))
        self.assertEqual(moonraker.pause_calls, 0)
        self.run_async(worker.process({"frame_id": 4, "result": self.result(0.70)}))
        self.assertEqual(moonraker.pause_calls, 1)
        self.run_async(worker.process({"frame_id": 5, "result": self.result(0.90)}))
        self.assertEqual(moonraker.pause_calls, 1)

    def test_time_confirmation_and_reset(self):
        clock = Clock()
        moonraker = FakeMoonraker()
        worker = FailureConfirmationWorker(moonraker, 0.60, "time", 10, 5, clock)
        self.run_async(worker.process(self.result(0.70)))
        clock.value = 4.9
        self.run_async(worker.process(self.result(0.70)))
        self.assertEqual(moonraker.pause_calls, 0)
        clock.value = 5
        self.run_async(worker.process(self.result(0.70)))
        self.assertEqual(moonraker.pause_calls, 1)

        clock = Clock()
        moonraker = FakeMoonraker()
        worker = FailureConfirmationWorker(moonraker, 0.60, "time", 10, 5, clock)
        self.run_async(worker.process(self.result(0.70)))
        clock.value = 2
        self.run_async(worker.process(self.result(0.40)))
        clock.value = 5
        self.run_async(worker.process(self.result(0.70)))
        self.assertEqual(moonraker.pause_calls, 0)

    def test_non_printing_and_failed_pause_are_safe(self):
        moonraker = FakeMoonraker(state="standby")
        worker = FailureConfirmationWorker(moonraker, 0.60, "frames", 1, 5)
        self.run_async(worker.process(self.result(0.90)))
        self.assertEqual(moonraker.pause_calls, 0)

        moonraker = FakeMoonraker(pause_result=False)
        worker = FailureConfirmationWorker(moonraker, 0.60, "frames", 1, 5)
        self.run_async(worker.process(self.result(0.90)))
        self.assertFalse(worker.pause_sent)

    def test_moonraker_endpoints_and_communication_errors(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.method, request.full_url, timeout))
            if request.method == "GET":
                return FakeResponse({"result": {"status": {"print_stats": {"state": "printing"}}}})
            return FakeResponse({"result": {}})

        client = MoonrakerClient("http://printer.local/", timeout=3)
        with patch("app.services.moonraker_client.urlopen", fake_urlopen):
            self.assertEqual(self.run_async(client.get_print_state()), "printing")
            self.run_async(client.pause_print())
        self.assertEqual(calls[0], ("GET", "http://printer.local/printer/objects/query?print_stats", 3))
        self.assertEqual(calls[1], ("POST", "http://printer.local/printer/print/pause", 3))

        with patch("app.services.moonraker_client.urlopen", side_effect=OSError("offline")):
            self.assertIsNone(self.run_async(client.safe_get_print_state()))
            self.assertFalse(self.run_async(client.safe_pause_print()))


if __name__ == "__main__":
    unittest.main()
