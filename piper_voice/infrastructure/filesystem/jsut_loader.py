"""JSUT corpus loader.

This module handles loading and parsing the JSUT (Japanese Speech Corpus
of Saruwatari Lab, University of Tokyo) corpus structure.

JSUT structure:
    jsut_ver1.1/
    ├── basic5000/
    │   ├── wav/
    │   │   ├── BASIC5000_0001.wav
    │   │   └── ...
    │   └── transcript_utf8.txt  (format: "AUDIO_ID:transcript_text")
    ├── onomatopee300/
    │   └── ...
    └── ...
"""

from pathlib import Path


class JsutCorpusLoader:
    """Loader for JSUT corpus.

    Parses JSUT directory structure and extracts audio-transcript pairs.
    """

    def __init__(self, jsut_root: Path) -> None:
        """Initialize JSUT loader.

        Args:
            jsut_root: Path to JSUT corpus root directory (jsut_ver1.1/)
        """
        self.jsut_root = jsut_root

    def load_corpus(self) -> list[tuple[Path, str]]:
        """Load all audio-transcript pairs from JSUT corpus.

        Returns:
            List of (audio_path, transcript) tuples

        Raises:
            FileNotFoundError: If JSUT directory doesn't exist
            ValueError: If no transcript files found
        """
        if not self.jsut_root.exists():
            raise FileNotFoundError(
                f"JSUT corpus directory not found: {self.jsut_root}"
            )

        # Find all transcript files recursively
        transcript_files = list(self.jsut_root.rglob("transcript_utf8.txt"))

        if not transcript_files:
            raise ValueError(
                f"No transcript files found in {self.jsut_root}. "
                "Expected files named 'transcript_utf8.txt'"
            )

        # Parse each transcript file
        pairs: list[tuple[Path, str]] = []

        for transcript_file in transcript_files:
            subset_pairs = self._parse_transcript_file(transcript_file)
            pairs.extend(subset_pairs)

        return pairs

    def _parse_transcript_file(self, transcript_file: Path) -> list[tuple[Path, str]]:
        """Parse a single transcript file and find corresponding audio.

        Args:
            transcript_file: Path to transcript_utf8.txt

        Returns:
            List of (audio_path, transcript) tuples for this subset
        """
        # Audio files are in sibling 'wav' directory
        wav_dir = transcript_file.parent / "wav"

        pairs: list[tuple[Path, str]] = []

        # Read and parse transcript file
        with open(transcript_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Parse format: "AUDIO_ID:transcript_text"
                if ":" not in line:
                    # Invalid format, skip
                    continue

                audio_id, transcript = line.split(":", 1)
                audio_id = audio_id.strip()
                transcript = transcript.strip()

                # Skip if transcript is empty
                if not transcript:
                    continue

                # Find corresponding audio file
                audio_file = wav_dir / f"{audio_id}.wav"

                if not audio_file.exists():
                    # Audio file missing, skip this pair
                    continue

                pairs.append((audio_file, transcript))

        return pairs

    def get_statistics(
        self, pairs: list[tuple[Path, str]]
    ) -> dict[str, int | dict[str, int]]:
        """Get statistics about loaded corpus.

        Args:
            pairs: List of loaded audio-transcript pairs

        Returns:
            Dictionary with corpus statistics
        """
        # Count samples per subset
        subset_counts: dict[str, int] = {}

        for audio_path, _ in pairs:
            # Subset name is parent.parent.name (e.g., "basic5000")
            subset_name = audio_path.parent.parent.name
            subset_counts[subset_name] = subset_counts.get(subset_name, 0) + 1

        return {
            "total_samples": len(pairs),
            "total_subsets": len(subset_counts),
            "subsets": subset_counts,
        }
