"""Unit tests for fixed voice selection in make_voice.py."""
import asyncio
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


# TTS is installed only in the generation workflow, so stub the import here.
_edge_tts_stub = types.ModuleType("edge_tts")
_edge_tts_stub.Communicate = None
with patch.dict(sys.modules, {"edge_tts": _edge_tts_stub}):
    make_voice = importlib.import_module("make_voice")


class FixedVoiceSelectionTest(unittest.TestCase):
    def test_voice_json_cannot_override_sardor_neural(self):
        calls = []

        class FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                calls.append((text, voice, kwargs))

            async def stream(self):
                yield {"type": "audio", "data": b"fake-audio"}
                yield {
                    "type": "WordBoundary",
                    "text": "Salom",
                    "offset": 0,
                    "duration": 10_000_000,
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir) / "video"
            folder.mkdir()
            (folder / "script.txt").write_text("Salom", encoding="utf-8")
            (folder / "voice.json").write_text(
                json.dumps({"voice": "en-US-AvaNeural", "rate": "-10%"}),
                encoding="utf-8",
            )

            with patch.object(make_voice.edge_tts, "Communicate", FakeCommunicate):
                asyncio.run(make_voice.make(folder))

            self.assertEqual(len(calls), 1)
            text, voice, options = calls[0]
            self.assertEqual(text, "Salom")
            self.assertEqual(voice, "uz-UZ-SardorNeural")
            self.assertEqual(options["rate"], "-10%")
            self.assertEqual((folder / "voice.mp3").read_bytes(), b"fake-audio")


if __name__ == "__main__":
    unittest.main()
