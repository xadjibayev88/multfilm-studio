#!/usr/bin/env python3
"""Compare Edge TTS audio with its script using local Whisper ASR.

Word differences are review flags, not proof of a TTS pronunciation error:
Whisper can also misrecognize Uzbek speech. A report is written beside each
voice.mp3 as voice_check.json; differences do not fail the workflow.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable

_WORD_RE = re.compile(r"[^\W_]+(?:['-][^\W_]+)*", flags=re.UNICODE)
_APOSTROPHE_TRANSLATION = str.maketrans({char: "'" for char in "’‘ʻʼ′ʹ"})
Transcriber = Callable[[Path], tuple[str, str | None]]


def _display_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text.translate(_APOSTROPHE_TRANSLATION))
    return _WORD_RE.findall(normalized)


def normalize_tokens(text: str) -> list[str]:
    """Return case-folded words with punctuation and apostrophe variants normalized."""
    return [word.casefold() for word in _display_tokens(text)]


def compare_text(script: str, transcript: str) -> dict:
    """Align two word sequences and report substitutions, omissions and insertions."""
    expected = _display_tokens(script)
    heard = _display_tokens(transcript)
    expected_keys = [word.casefold() for word in expected]
    heard_keys = [word.casefold() for word in heard]
    n, m = len(expected), len(heard)

    # Levenshtein alignment at the word level: substitution, deletion, insertion.
    costs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        costs[i][0] = i
    for j in range(m + 1):
        costs[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            substitution = costs[i - 1][j - 1] + (expected_keys[i - 1] != heard_keys[j - 1])
            deletion = costs[i - 1][j] + 1
            insertion = costs[i][j - 1] + 1
            costs[i][j] = min(substitution, deletion, insertion)

    differences: list[dict[str, str]] = []
    substitutions = deletions = insertions = 0
    i, j = n, m
    while i or j:
        # Prefer a tied insertion/deletion over a substitution. This keeps an
        # extra recognized word from shifting the following expected word.
        if j and costs[i][j] == costs[i][j - 1] + 1:
            differences.append({"type": "extra", "expected": "", "heard": heard[j - 1]})
            insertions += 1
            j -= 1
            continue
        if i and costs[i][j] == costs[i - 1][j] + 1:
            differences.append({"type": "missing", "expected": expected[i - 1], "heard": ""})
            deletions += 1
            i -= 1
            continue
        if i and j:
            step_cost = 0 if expected_keys[i - 1] == heard_keys[j - 1] else 1
            if costs[i][j] == costs[i - 1][j - 1] + step_cost:
                if step_cost:
                    differences.append({
                        "type": "different",
                        "expected": expected[i - 1],
                        "heard": heard[j - 1],
                    })
                    substitutions += 1
                i -= 1
                j -= 1
                continue

    differences.reverse()
    error_count = substitutions + deletions + insertions
    denominator = max(1, n)
    return {
        "status": "review" if error_count else "ok",
        "expected_word_count": n,
        "transcribed_word_count": m,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "error_count": error_count,
        "word_error_rate": round(error_count / denominator, 4),
        "transcript": transcript,
        "differences": differences,
    }


def _make_transcriber(model_name: str, language: str, compute_type: str, cpu_threads: int) -> Transcriber:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Whisper dependency missing; install faster-whisper before running this check."
        ) from exc

    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type=compute_type,
        cpu_threads=cpu_threads,
    )

    def transcribe(audio_path: Path) -> tuple[str, str | None]:
        segments, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, getattr(info, "language", language)

    return transcribe


def run_checks(root: Path, transcriber: Transcriber, model_name: str, language: str) -> list[dict]:
    reports: list[dict] = []
    scripts = sorted(root.glob("*/script.txt"))
    for script_path in scripts:
        audio_path = script_path.parent / "voice.mp3"
        if not audio_path.is_file():
            reports.append({"voice": script_path.parent.name, "status": "skipped", "reason": "voice.mp3 not found"})
            continue

        try:
            transcript, detected_language = transcriber(audio_path)
            report = compare_text(script_path.read_text(encoding="utf-8"), transcript)
            report.update({
                "voice": script_path.parent.name,
                "script": script_path.name,
                "audio": audio_path.name,
                "model": model_name,
                "language": detected_language or language,
                "note": "Differences are review flags; Whisper may also misrecognize speech.",
            })
        except Exception as exc:  # Keep the other voice checks running; surface this as a tool error.
            report = {
                "voice": script_path.parent.name,
                "script": script_path.name,
                "audio": audio_path.name,
                "model": model_name,
                "language": language,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

        report_path = script_path.parent / "voice_check.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        reports.append(report)
    return reports


def format_summary(reports: list[dict]) -> str:
    lines = ["### Whisper voice check", "", "Word mismatches are review flags, not confirmed pronunciation errors.", ""]
    if not reports:
        lines.append("No `voices/*/script.txt` files found.")
        return "\n".join(lines) + "\n"

    for report in reports:
        name = report["voice"]
        status = report["status"]
        if status == "ok":
            lines.append(f"- **{name}**: no word differences detected ({report['expected_word_count']} words).")
        elif status == "review":
            lines.append(
                f"- **{name}**: review {report['error_count']} possible difference(s); "
                f"WER {report['word_error_rate']:.1%}."
            )
            for difference in report["differences"]:
                if difference["type"] == "missing":
                    description = f"possibly missing ‘{difference['expected']}’"
                elif difference["type"] == "extra":
                    description = f"unexpected ‘{difference['heard']}’"
                else:
                    description = f"script ‘{difference['expected']}’ / heard ‘{difference['heard']}’"
                lines.append(f"  - {description}")
        elif status == "skipped":
            lines.append(f"- **{name}**: skipped — {report['reason']}.")
        else:
            lines.append(f"- **{name}**: check failed — {report.get('error', 'unknown error')}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Edge TTS audio with its script using local Whisper.")
    parser.add_argument("root", nargs="?", default="voices", help="folder containing voice subfolders")
    parser.add_argument("--model", default="small", help="faster-whisper model size/name (default: small)")
    parser.add_argument("--language", default="uz", help="spoken language code (default: uz)")
    parser.add_argument("--compute-type", default="int8", help="CPU inference type (default: int8)")
    parser.add_argument("--cpu-threads", type=int, default=4, help="CPU threads (default: 4)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    scripts_with_audio = [path for path in root.glob("*/script.txt") if (path.parent / "voice.mp3").is_file()]
    if not scripts_with_audio:
        reports = run_checks(root, lambda _path: ("", args.language), args.model, args.language)
    else:
        try:
            transcriber = _make_transcriber(args.model, args.language, args.compute_type, args.cpu_threads)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        reports = run_checks(root, transcriber, args.model, args.language)

    summary = format_summary(reports)
    print(summary, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as output:
            output.write(summary)
    return 1 if any(report["status"] == "error" for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
