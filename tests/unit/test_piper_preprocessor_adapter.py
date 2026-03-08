"""Unit tests for PiperPreprocessorAdapter.

Following TDD: These tests are written BEFORE implementation.
Tests CSV → JSONL transformation for Piper preprocessing.
"""

import json
from pathlib import Path

import pytest

from piper_voice.infrastructure.piper.preprocessor_adapter import (
    PiperPreprocessorAdapter,
)


class TestPiperPreprocessorAdapter:
    """Tests for PiperPreprocessorAdapter."""

    def test_adapter_creation(self) -> None:
        """Test creating PiperPreprocessorAdapter."""
        adapter = PiperPreprocessorAdapter()
        assert adapter is not None

    def test_transform_simple_metadata(self, tmp_path: Path) -> None:
        """Test transforming simple metadata CSV to JSONL."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Create test audio files
        (audio_dir / "audio_001.wav").touch()
        (audio_dir / "audio_002.wav").touch()

        # Create metadata
        input_csv.write_text(
            "audio_001.wav|0 1 2\n" "audio_002.wav|3 4 5\n", encoding="utf-8"
        )

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        assert output_jsonl.exists()

    def test_jsonl_format_is_valid(self, tmp_path: Path) -> None:
        """Test that output JSONL has valid format."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()
        input_csv.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert - Load and verify JSONL
        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        # Parse JSON
        entry = json.loads(lines[0])
        assert "audio_file" in entry
        assert "phoneme_ids" in entry

    def test_jsonl_contains_correct_audio_path(self, tmp_path: Path) -> None:
        """Test that JSONL contains correct audio file path."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()
        input_csv.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])

        # Audio path should be relative or absolute
        assert entry["audio_file"].endswith("audio_001.wav")

    def test_jsonl_contains_phoneme_ids_as_list(self, tmp_path: Path) -> None:
        """Test that phoneme_ids are stored as list of integers."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()
        input_csv.write_text("audio_001.wav|0 12 5 8 14\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["phoneme_ids"] == [0, 12, 5, 8, 14]
        assert all(isinstance(x, int) for x in entry["phoneme_ids"])

    def test_transform_multiple_entries(self, tmp_path: Path) -> None:
        """Test transforming multiple metadata entries."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Create test audio files
        for i in range(5):
            (audio_dir / f"audio_{i:03d}.wav").touch()

        # Create metadata
        lines = [f"audio_{i:03d}.wav|{i} {i+1} {i+2}\n" for i in range(5)]
        input_csv.write_text("".join(lines), encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        jsonl_lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(jsonl_lines) == 5

        # Verify each entry
        for i, line in enumerate(jsonl_lines):
            entry = json.loads(line)
            assert f"audio_{i:03d}.wav" in entry["audio_file"]
            assert entry["phoneme_ids"] == [i, i + 1, i + 2]

    def test_transform_validates_audio_file_exists(self, tmp_path: Path) -> None:
        """Test that transform validates audio files exist."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Missing audio file
        input_csv.write_text("missing.wav|0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            adapter.transform_to_jsonl(
                input_metadata=input_csv,
                output_jsonl=output_jsonl,
                audio_dir=audio_dir,
            )

    def test_transform_rejects_empty_metadata(self, tmp_path: Path) -> None:
        """Test that empty metadata raises error."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        input_csv.write_text("", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act & Assert
        with pytest.raises(ValueError, match="No entries found"):
            adapter.transform_to_jsonl(
                input_metadata=input_csv,
                output_jsonl=output_jsonl,
                audio_dir=audio_dir,
            )

    def test_transform_rejects_malformed_csv(self, tmp_path: Path) -> None:
        """Test that malformed CSV raises error."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Missing pipe separator
        input_csv.write_text("audio_001.wav 0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid metadata format"):
            adapter.transform_to_jsonl(
                input_metadata=input_csv,
                output_jsonl=output_jsonl,
                audio_dir=audio_dir,
            )

    def test_transform_rejects_invalid_phoneme_ids(self, tmp_path: Path) -> None:
        """Test that invalid phoneme IDs raise error."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()

        # Non-integer phoneme ID
        input_csv.write_text("audio_001.wav|0 abc 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid phoneme ID"):
            adapter.transform_to_jsonl(
                input_metadata=input_csv,
                output_jsonl=output_jsonl,
                audio_dir=audio_dir,
            )

    def test_transform_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that transform creates parent directory if needed."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "subdir" / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()
        input_csv.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        assert output_jsonl.exists()
        assert output_jsonl.parent.exists()

    def test_transform_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Test that transformation is deterministic."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        (audio_dir / "audio_001.wav").touch()
        input_csv.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act - Transform twice
        output1 = tmp_path / "dataset1.jsonl"
        output2 = tmp_path / "dataset2.jsonl"

        adapter.transform_to_jsonl(
            input_metadata=input_csv, output_jsonl=output1, audio_dir=audio_dir
        )

        adapter.transform_to_jsonl(
            input_metadata=input_csv, output_jsonl=output2, audio_dir=audio_dir
        )

        # Assert - Outputs should be identical
        content1 = output1.read_text(encoding="utf-8")
        content2 = output2.read_text(encoding="utf-8")
        assert content1 == content2

    def test_transform_handles_large_dataset(self, tmp_path: Path) -> None:
        """Test transforming large dataset (1000 entries)."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Create 1000 entries
        lines = []
        for i in range(1000):
            (audio_dir / f"audio_{i:04d}.wav").touch()
            lines.append(f"audio_{i:04d}.wav|{i % 100} {(i+1) % 100}\n")

        input_csv.write_text("".join(lines), encoding="utf-8")

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert
        jsonl_lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(jsonl_lines) == 1000

    def test_jsonl_one_entry_per_line(self, tmp_path: Path) -> None:
        """Test that JSONL has exactly one JSON object per line."""
        # Arrange
        input_csv = tmp_path / "metadata_phonemes.csv"
        output_jsonl = tmp_path / "dataset.jsonl"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        for i in range(3):
            (audio_dir / f"audio_{i}.wav").touch()

        input_csv.write_text(
            "audio_0.wav|0 1\n" "audio_1.wav|2 3\n" "audio_2.wav|4 5\n",
            encoding="utf-8",
        )

        adapter = PiperPreprocessorAdapter()

        # Act
        adapter.transform_to_jsonl(
            input_metadata=input_csv,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
        )

        # Assert - Each line should be valid JSON
        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        for line in lines:
            entry = json.loads(line)  # Should not raise
            assert isinstance(entry, dict)
