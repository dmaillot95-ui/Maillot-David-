import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cerebron.inference_hub.hub as hub


class HubTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.queue = self.tmp_path / "queue.json"
        self.latest = self.tmp_path / "latest.json"
        self.config = self.tmp_path / "config.json"
        self.config.write_text(json.dumps({
            "max_logical_agents": 10000,
            "micro_batch_size": 4,
            "max_parallel_workers": 4,
            "wave_delay_seconds": 0,
            "max_attempts_per_task": 3,
        }), encoding="utf-8")
        self.patches = [
            mock.patch.object(hub, "QUEUE_PATH", self.queue),
            mock.patch.object(hub, "LATEST_PATH", self.latest),
            mock.patch.object(hub, "CONFIG_PATH", self.config),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_enqueue_1000_logical_agents(self):
        created = hub.enqueue("M1", "test", 1000)
        self.assertEqual(len(created), 1000)
        state = hub.status()
        self.assertEqual(state["tasks"], 1000)
        self.assertEqual(state["status"]["PENDING"], 1000)

    def test_enqueue_is_idempotent(self):
        self.assertEqual(len(hub.enqueue("M1", "same", 20)), 20)
        self.assertEqual(len(hub.enqueue("M1", "same", 20)), 0)
        self.assertEqual(hub.status()["tasks"], 20)

    def test_agent_limit_is_enforced(self):
        created = hub.enqueue("M2", "limit", 10001)
        self.assertEqual(len(created), 10000)


if __name__ == "__main__":
    unittest.main()
