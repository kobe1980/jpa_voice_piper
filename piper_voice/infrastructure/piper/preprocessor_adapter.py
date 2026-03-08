"""Piper preprocessor adapter for CSV → JSONL transformation.

This module transforms metadata_phonemes.csv (audio_file|phoneme_ids)
into Piper's expected dataset.jsonl format (line-delimited JSON).
"""

import json
from pathlib import Path


class PiperPreprocessorAdapter:
    """Adapter for transforming metadata to Piper JSONL format.

    Transforms CSV format (audio_file|phoneme_ids) into JSONL format
    where each line is a JSON object with audio file path and phoneme IDs.
    """

    def transform_to_jsonl(
        self,
        input_metadata: Path,
        output_jsonl: Path,
        audio_dir: Path,
    ) -> None:
        """Transform metadata CSV to Piper JSONL format.

        Args:
            input_metadata: Path to metadata_phonemes.csv
            output_jsonl: Path to output dataset.jsonl
            audio_dir: Directory containing audio files

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
                raise FileNotFoundError(
                    f"Audio file not found: {audio_path} (line {line_num})"
                )

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
