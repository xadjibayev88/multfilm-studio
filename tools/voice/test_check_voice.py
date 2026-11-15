import json
import tempfile
import unittest
from pathlib import Path

from check_voice import compare_text, format_summary, normalize_tokens, run_checks


class NormalizeTokensTests(unittest.TestCase):
    def test_case_punctuation_and_uzbek_apostrophe_variants_are_normalized(self):
        self.assertEqual(
            normalize_tokens("O‘zbekcha, Gʻalati! O'ZBEKCHA."),
            ["o'zbekcha", "g'alati", "o'zbekcha"],
        )


class CompareTextTests(unittest.TestCase):
    def test_identical_text_with_punctuation_differences_has_no_flags(self):
        report = compare_text("Bir oddiy tosh sotildi.", "BIR, oddiy tosh sotildi")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["word_error_rate"], 0.0)
        self.assertEqual(report["differences"], [])

    def test_missing_word_is_flagged(self):
        report = compare_text("Bir oddiy tosh sotildi", "Bir tosh sotildi")
        self.assertEqual(report["status"], "review")
        self.assertEqual(report["deletions"], 1)
        self.assertIn(
            {"type": "missing", "expected": "oddiy", "heard": ""},
            report["differences"],
        )

    def test_substitution_and_unexpected_word_are_flagged(self):
        report = compare_text("Geri Dal tosh sotdi", "Geri Dell yangi tosh sotdi")
        self.assertEqual(report["substitutions"], 1)
        self.assertEqual(report["insertions"], 1)
        self.assertIn(
            {"type": "different", "expected": "Dal", "heard": "Dell"},
            report["differences"],
        )
        self.assertIn(
            {"type": "extra", "expected": "", "heard": "yangi"},
            report["differences"],
        )

    def test_empty_text_is_safe(self):
        report = compare_text("", "")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["word_error_rate"], 0.0)


class RunChecksTests(unittest.TestCase):
    def test_writes_json_report_and_marks_mismatch_for_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            voice = root / "demo"
            voice.mkdir()
            (voice / "script.txt").write_text("Bir oddiy tosh", encoding="utf-8")
            (voice / "voice.mp3").write_bytes(b"test audio placeholder")

            reports = run_checks(
                root,
                lambda _audio: ("Bir tosh", "uz"),
                "small",
                "uz",
            )

            saved = json.loads((voice / "voice_check.json").read_text(encoding="utf-8"))
            self.assertEqual(reports[0]["status"], "review")
            self.assertEqual(saved["differences"][0]["expected"], "oddiy")
            self.assertIn("Whisper may also misrecognize", saved["note"])
            self.assertIn("possibly missing ‘oddiy’", format_summary(reports))


if __name__ == "__main__":
    unittest.main()
