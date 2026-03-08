"""Piper preprocessor adapter for CSV → JSONL transformation.

This module transforms metadata_phonemes.csv (audio_file|phoneme_ids)
into Piper's expected dataset.jsonl format (line-delimited JSON).
"""

import json
import logging
import wave
from pathlib import Path

logger = logging.getLogger(__name__)


class PiperPreprocessorAdapter:
    """Adapter for transforming metadata to Piper JSONL format.

    Transforms CSV format (audio_file|phoneme_ids) into JSONL format
    where each line is a JSON object with audio file path and phoneme IDs.
    """

    def _is_valid_wav_file(self, audio_path: Path) -> bool:
        """Check if a WAV file is valid and can be opened.

        Args:
            audio_path: Path to WAV file

        Returns:
            True if file is valid, False if corrupted
        """
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                # Try to read basic properties
                _ = wav_file.getframerate()
                _ = wav_file.getnchannels()
                _ = wav_file.getsampwidth()
                _ = wav_file.getnframes()
            return True
        except wave.Error:
            return False

    def transform_to_jsonl(
        self,
        input_metadata: Path,
        output_jsonl: Path,
        audio_dir: Path,
        validate_audio: bool = False,
    ) -> dict:
        """Transform metadata CSV to Piper JSONL format.

        Args:
            input_metadata: Path to metadata_phonemes.csv
            output_jsonl: Path to output dataset.jsonl
            audio_dir: Directory containing audio files
            validate_audio: If True, validate WAV files and skip corrupted ones

        Returns:
            Dictionary with transformation results:
                - total_entries: Total valid entries written
                - skipped_entries: Number of entries skipped
                - corrupted_files: List of corrupted filenames

        Raises:
            FileNotFoundError: If metadata or audio files not found
            ValueError: If metadata format is invalid
        """
        # Read metadata
        if not input_metadata.exists():
            raise FileNotFoundError(f"Metadata file not found: {input_metadata}")

        lines = input_metadata.read_text(encoding="utf-8").strip().split("\n")

        if not lines or (len(lines) == 1 and not lines[0]):
            raise ValueError("No entries found in metadata")

        # Parse and transform entries
        jsonl_entries = []
        corrupted_files = []
        skipped_entries = 0

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            # Parse CSV line
            parts = line.split("|")
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid metadata format at line {line_num}: "
                    f"expected 'audio_file|phoneme_ids', got '{line}'"
                )

            audio_filename, phoneme_ids_str = parts

            # Validate audio file exists
            audio_path = audio_dir / audio_filename
            if not audio_path.exists():
                audio_path = audio_dir / f"{audio_filename}.wav"
            if not audio_path.exists():
                raise FileNotFoundError(
                    f"Audio file not found: {audio_path} (line {line_num})"
                )

            # Validate audio if requested
            if validate_audio and not self._is_valid_wav_file(audio_path):
                logger.warning(
                    "Skipping corrupted WAV file %s (line %d)",
                    audio_path.name,
                    line_num,
                )
                corrupted_files.append(audio_path.name)
                skipped_entries += 1
                continue

            # Parse phoneme IDs
            try:
                phoneme_ids = [int(x) for x in phoneme_ids_str.split()]
            except ValueError as e:
                raise ValueError(
                    f"Invalid phoneme ID at line {line_num}: {e}"
                ) from e

            # Create JSONL entry
            entry = {
                "audio_file": str(audio_path),
                "phoneme_ids": phoneme_ids,
            }

            jsonl_entries.append(entry)

        # Create parent directory if needed
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)

        # Write JSONL (one JSON object per line)
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for entry in jsonl_entries:
                json_line = json.dumps(entry, ensure_ascii=False)
                f.write(json_line + "\n")

        # Return transformation results
        return {
            "total_entries": len(jsonl_entries),
            "skipped_entries": skipped_entries,
            "corrupted_files": corrupted_files,
        }
