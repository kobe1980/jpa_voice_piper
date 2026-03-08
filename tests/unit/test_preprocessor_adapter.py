"""Unit tests for PreprocessorAdapter.

Following TDD: These tests are written BEFORE implementation.
Tests dataset preparation and JSONL generation for Piper training.
"""

import json
import wave
from pathlib import Path

import numpy as np
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

    def test_transform_to_jsonl_excludes_corrupted_files(
        self, tmp_path: Path
    ) -> None:
        """Test that corrupted files are excluded from dataset.jsonl.

        This is a CRITICAL test for the current bug:
        - AudioStatsCalculator skips corrupted files during stats calculation
        - But dataset.jsonl still includes them, causing training to fail
        - PiperPreprocessorAdapter MUST exclude corrupted files from dataset.jsonl
        """
        # Arrange - Create metadata with 2 files (1 good, 1 corrupted)
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Good file
        good_file = audio_dir / "good.wav"
        self._create_test_wav(good_file, duration_ms=1000, sample_rate=22050)

        # Corrupted file (invalid WAV structure)
        bad_file = audio_dir / "bad.wav"
        bad_file.write_bytes(
            b"RIFF" + (8).to_bytes(4, "little") + b"WAVE" + b"\x00" * 100
        )

        # Metadata CSV with both files
        metadata_path = tmp_path / "metadata.csv"
        metadata_path.write_text(
            "good.wav|1 2 3\n"
            "bad.wav|4 5 6\n",
            encoding="utf-8"
        )

        output_jsonl = tmp_path / "dataset.jsonl"
        adapter = PiperPreprocessorAdapter()

        # Act - Transform metadata to JSONL
        # Should skip corrupted file automatically
        result = adapter.transform_to_jsonl(
            input_metadata=metadata_path,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
            validate_audio=True,  # Enable audio validation
        )

        # Assert - Only good file should be in JSONL
        assert output_jsonl.exists()

        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1, "Should have only 1 entry (corrupted file excluded)"

        entry = json.loads(lines[0])
        assert "good.wav" in entry["audio_file"]

        # Result should indicate 1 file was skipped
        assert result["corrupted_files"] == ["bad.wav"]
        assert result["total_entries"] == 1
        assert result["skipped_entries"] == 1

    def test_transform_to_jsonl_with_all_valid_files(
        self, tmp_path: Path
    ) -> None:
        """Test dataset.jsonl creation when all files are valid."""
        # Arrange
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Create 3 valid files
        for i in range(3):
            audio_file = audio_dir / f"test_{i}.wav"
            self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        metadata_path = tmp_path / "metadata.csv"
        metadata_path.write_text(
            "test_0.wav|1 2 3\n"
            "test_1.wav|4 5 6\n"
            "test_2.wav|7 8 9\n",
            encoding="utf-8"
        )

        output_jsonl = tmp_path / "dataset.jsonl"
        adapter = PiperPreprocessorAdapter()

        # Act
        result = adapter.transform_to_jsonl(
            input_metadata=metadata_path,
            output_jsonl=output_jsonl,
            audio_dir=audio_dir,
            validate_audio=True,
        )

        # Assert - All files should be in JSONL
        assert output_jsonl.exists()
        lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        assert result["corrupted_files"] == []
        assert result["total_entries"] == 3
        assert result["skipped_entries"] == 0

    def test_transform_to_jsonl_validates_metadata_path(
        self, tmp_path: Path
    ) -> None:
        """Test that missing metadata file raises error."""
        adapter = PiperPreprocessorAdapter()

        missing_path = tmp_path / "missing.csv"
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()
        output_jsonl = tmp_path / "dataset.jsonl"

        with pytest.raises(FileNotFoundError):
            adapter.transform_to_jsonl(
                input_metadata=missing_path,
                output_jsonl=output_jsonl,
                audio_dir=audio_dir,
            )

    # Helper methods

    def _create_test_wav(
        self, path: Path, duration_ms: int, sample_rate: int
    ) -> None:
        """Create a test WAV file.

        Args:
            path: Output path
            duration_ms: Duration in milliseconds
            sample_rate: Sample rate in Hz
        """
        num_samples = int(sample_rate * duration_ms / 1000)
        # Generate simple sine wave
        frequency = 440.0  # A4 note
        samples = np.sin(2 * np.pi * frequency * np.arange(num_samples) / sample_rate)

        # Convert to 16-bit PCM
        samples_int16 = (samples * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_int16.tobytes())
