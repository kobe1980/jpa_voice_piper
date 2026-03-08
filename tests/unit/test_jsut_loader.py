"""Unit tests for JSUT corpus loader.

Following TDD: These tests are written BEFORE implementation.
Tests the JSUT-specific corpus parsing and loading.
"""

from pathlib import Path

import pytest

from piper_voice.infrastructure.filesystem.jsut_loader import JsutCorpusLoader


@pytest.fixture
def create_jsut_structure(tmp_path: Path):
    """Factory fixture to create mock JSUT corpus structure."""

    def _create(num_files: int = 3) -> Path:
        """Create a minimal JSUT corpus structure for testing.

        Args:
            num_files: Number of audio files to create per subset

        Returns:
            Path to JSUT root directory
        """
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        # JSUT has multiple subsets, create one for testing
        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        # Create transcript file
        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"

        transcript_lines = []
        for i in range(num_files):
            audio_id = f"BASIC5000_{i:04d}"

            # Create audio file
            audio_file = subset_dir / f"{audio_id}.wav"
            audio_file.write_bytes(b"fake wav data")

            # Add transcript line
            transcript_lines.append(f"{audio_id}:これはテストです{i}")

        transcript_file.write_text("\n".join(transcript_lines), encoding="utf-8")

        return jsut_root

    return _create


class TestJsutCorpusLoader:
    """Tests for JsutCorpusLoader."""

    def test_load_corpus_finds_audio_files(self, create_jsut_structure) -> None:
        """Test that loader finds all audio files."""
        jsut_root = create_jsut_structure(num_files=5)

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        assert len(pairs) == 5

    def test_load_corpus_returns_audio_text_pairs(self, create_jsut_structure) -> None:
        """Test that loader returns (audio_path, transcript) tuples."""
        jsut_root = create_jsut_structure(num_files=3)

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Check structure
        assert all(isinstance(pair, tuple) for pair in pairs)
        assert all(len(pair) == 2 for pair in pairs)

        # Check types
        audio_path, transcript = pairs[0]
        assert isinstance(audio_path, Path)
        assert isinstance(transcript, str)

    def test_load_corpus_parses_transcript_format(self, create_jsut_structure) -> None:
        """Test that loader correctly parses 'AUDIO_ID:text' format."""
        jsut_root = create_jsut_structure(num_files=2)

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Check transcripts
        transcripts = [pair[1] for pair in pairs]
        assert "これはテストです0" in transcripts
        assert "これはテストです1" in transcripts

    def test_load_corpus_matches_audio_to_transcript(
        self, create_jsut_structure
    ) -> None:
        """Test that audio files are correctly matched to transcripts."""
        jsut_root = create_jsut_structure(num_files=3)

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Check that each audio file exists
        for audio_path, _transcript in pairs:
            assert audio_path.exists()
            assert audio_path.suffix == ".wav"

    def test_load_corpus_skips_missing_audio(self, tmp_path: Path) -> None:
        """Test that loader skips transcripts with missing audio files."""
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        # Create transcript with 3 entries but only 2 audio files
        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_file.write_text(
            "BASIC5000_0000:テスト0\nBASIC5000_0001:テスト1\nBASIC5000_0002:テスト2\n",
            encoding="utf-8",
        )

        # Create only 2 audio files (missing 0001)
        (subset_dir / "BASIC5000_0000.wav").write_bytes(b"data")
        (subset_dir / "BASIC5000_0002.wav").write_bytes(b"data")

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Should only load 2 pairs (skip missing 0001)
        assert len(pairs) == 2

        # Check we got the right ones
        audio_ids = [path.stem for path, _ in pairs]
        assert "BASIC5000_0000" in audio_ids
        assert "BASIC5000_0002" in audio_ids
        assert "BASIC5000_0001" not in audio_ids

    def test_load_corpus_handles_multiple_subsets(self, tmp_path: Path) -> None:
        """Test that loader handles multiple JSUT subsets."""
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        # Create two subsets
        for subset_name in ["basic5000", "onomatopee300"]:
            subset_dir = jsut_root / subset_name / "wav"
            subset_dir.mkdir(parents=True)

            transcript_file = jsut_root / subset_name / "transcript_utf8.txt"
            transcript_file.write_text(
                f"{subset_name.upper()}_0000:テスト{subset_name}", encoding="utf-8"
            )

            (subset_dir / f"{subset_name.upper()}_0000.wav").write_bytes(b"data")

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Should find files from both subsets
        assert len(pairs) == 2

        transcripts = [pair[1] for pair in pairs]
        assert any("basic5000" in t for t in transcripts)
        assert any("onomatopee300" in t for t in transcripts)

    def test_load_corpus_raises_on_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that loading from nonexistent directory raises error."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="JSUT corpus directory not found"):
            loader = JsutCorpusLoader(nonexistent)
            loader.load_corpus()

    def test_load_corpus_raises_on_empty_directory(self, tmp_path: Path) -> None:
        """Test that loading from empty directory raises error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = JsutCorpusLoader(empty_dir)

        with pytest.raises(ValueError, match="No transcript files found"):
            loader.load_corpus()

    def test_load_corpus_cleans_whitespace_in_transcripts(
        self, create_jsut_structure
    ) -> None:
        """Test that loader cleans extra whitespace from transcripts."""
        jsut_root = create_jsut_structure(num_files=1)

        # Modify transcript to have extra whitespace
        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_file.write_text(
            "BASIC5000_0000:  これは　　テストです  ", encoding="utf-8"
        )

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        # Transcript should be cleaned
        transcript = pairs[0][1]
        assert (
            transcript == "これは　　テストです"
        )  # Internal spaces preserved, edges trimmed

    def test_get_statistics_returns_corpus_info(self, create_jsut_structure) -> None:
        """Test that statistics method returns corpus information."""
        jsut_root = create_jsut_structure(num_files=10)

        loader = JsutCorpusLoader(jsut_root)
        pairs = loader.load_corpus()

        stats = loader.get_statistics(pairs)

        assert isinstance(stats, dict)
        assert stats["total_samples"] == 10
        assert stats["total_subsets"] >= 1
        assert "subsets" in stats
