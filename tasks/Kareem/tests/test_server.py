"""
test_server.py — Unit and integration tests for Kareem's service.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

kareem_root = Path(__file__).resolve().parent.parent
if str(kareem_root) not in sys.path:
    sys.path.insert(0, str(kareem_root))

from challenge_generator.agent import calibrate_difficulty
from solution_reviewer.agent import analyze_code_quality
from challenge_generator.server import app, DEFAULT_LEADERBOARD

class TestKareemServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_calibrate_difficulty(self):
        desc = "Write a function that solves a dynamic programming problem with constraints on memory and handles null input."
        res = calibrate_difficulty("Dynamic Programming", "hard", desc)
        self.assertIn("Score", res)

    def test_analyze_code_quality(self):
        code = "def add(a: int, b: int) -> int:\n    \"\"\"Add two integers.\"\"\"\n    return a + b\n"
        res = analyze_code_quality(code, "python")
        self.assertIn("Quality:", res)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_save_and_get_challenge(self):
        payload = {
            "topic": "Arrays & Strings",
            "difficulty": "easy",
            "description": "Reverse a string in place",
            "solution": "def rev(s): return s[::-1]"
        }
        res_save = self.client.post("/save", json=payload)
        self.assertEqual(res_save.status_code, 200)
        self.assertEqual(res_save.json()["status"], "saved")

        res_push = self.client.post("/challenge", json=payload)
        self.assertEqual(res_push.status_code, 200)
        self.assertEqual(res_push.json()["status"], "posted")

        res_get = self.client.get("/challenge")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["topic"], "Arrays & Strings")

    def test_leaderboard(self):
        res = self.client.get("/leaderboard")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_award_xp(self):
        xp_payload = {
            "name": "Kareem",
            "xp_awarded": 15,
            "commit_count": 1,
            "files_changed": 2,
            "commit_sha": "sha_test_999"
        }
        res = self.client.post("/xp", json=xp_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "awarded")

    def test_webhook_ping(self):
        headers = {"X-GitHub-Event": "ping"}
        res = self.client.post("/github_webhook", json={}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "pong"})


if __name__ == "__main__":
    unittest.main()
