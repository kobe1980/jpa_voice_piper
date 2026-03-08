"""LJSPEECH metadata writer for Piper.

This module handles writing metadata.csv in LJSPEECH format:
- Format: filename|transcript (one per line)
- Encoding: UTF-8
- No header row
- Filenames without .wav extension
"""

from pathlib import Path


class LJSpeechMetadataWriter:
    """Writer for LJSPEECH format metadata.csv.

    Generates metadata.csv file required by Piper preprocessing.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize metadata writer.

        Args:
            output_dir: Directory where metadata.csv will be written
        """
        self.output_dir = output_dir

    def write_metadata(self, pairs: list[tuple[Path, str]]) -> None:
        """Write audio-transcript pairs to metadata.csv.

        Args:
            pairs: List of (audio_path, transcript) tuples

        Raises:
            ValueError: If transcript is empty or contains invalid characters
        """
        # Validate all pairs before writing (atomic operation)
        validated_lines: list[str] = []

        for audio_path, transcript in pairs:
            # Validate transcript
            transcript_clean = transcript.strip()

            if not transcript_clean:
                raise ValueError(
                    f"Empty transcript for {audio_path}. "
                    "All transcripts must contain text."
                )

            # Check for pipe character (conflicts with LJSPEECH format)
            if "|" in transcript_clean:
                raise ValueError(
                    f"Transcript contains pipe character '|' for {audio_path}. "
                    "Pipe character is reserved for LJSPEECH format separator."
                )

            # Format: filename (without .wav)|transcript
            filename = audio_path.stem  # Remove extension
            line = f"{filename}|{transcript_clean}"
            validated_lines.append(line)

        # Write to file
        metadata_file = self.output_dir / "metadata.csv"

        with open(metadata_file, "w", encoding="utf-8") as f:
            for line in validated_lines:
                f.write(line + "\n")
