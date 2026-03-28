"""Unit tests for AudioStatsCalculator.

Following TDD: These tests are written BEFORE implementation.
Tests audio normalization statistics calculation for Piper preprocessing.
"""

import wave
from pathlib import Path

import numpy as np
import pytest

from piper_voice.infrastructure.piper.audio_stats import AudioStatsCalculator


class TestAudioStatsCalculator:
    """Tests for AudioStatsCalculator."""

    def test_calculator_creation(self) -> None:
        """Test creating AudioStatsCalculator."""
        calculator = AudioStatsCalculator()
        assert calculator is not None

    def test_calculate_stats_single_file(self, tmp_path: Path) -> None:
        """Test calculating stats for single audio file."""
        # Arrange - Create test WAV file
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()

        # Act
        stats = calculator.calculate_stats([audio_file])

        # Assert
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_calculate_stats_multiple_files(self, tmp_path: Path) -> None:
        """Test calculating stats across multiple files."""
        # Arrange - Create multiple test files
        files = []
        for i in range(5):
            audio_file = tmp_path / f"test_{i}.wav"
            self._create_test_wav(audio_file, duration_ms=500, sample_rate=22050)
            files.append(audio_file)

        calculator = AudioStatsCalculator()

        # Act
        stats = calculator.calculate_stats(files)

        # Assert
        assert isinstance(stats["mean"], float)
        assert isinstance(stats["std"], float)
        assert isinstance(stats["min"], float)
        assert isinstance(stats["max"], float)

    def test_stats_values_are_reasonable(self, tmp_path: Path) -> None:
        """Test that calculated stats have reasonable values."""
        # Arrange
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()

        # Act
        stats = calculator.calculate_stats([audio_file])

        # Assert - Stats should be in valid ranges
        assert -1.0 <= stats["mean"] <= 1.0
        assert 0.0 <= stats["std"] <= 1.0
        assert -1.0 <= stats["min"] <= 1.0
        assert -1.0 <= stats["max"] <= 1.0
        assert stats["min"] <= stats["mean"] <= stats["max"]

    def test_calculate_stats_validates_sample_rate(self, tmp_path: Path) -> None:
        """Test that calculator validates sample rate."""
        # Arrange - Create file with wrong sample rate
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=44100)

        calculator = AudioStatsCalculator()

        # Act & Assert
        with pytest.raises(ValueError, match="Sample rate must be"):
            calculator.calculate_stats([audio_file], expected_sample_rate=22050)

    def test_calculate_stats_with_empty_file_list_raises_error(self) -> None:
        """Test that empty file list raises error."""
        calculator = AudioStatsCalculator()

        with pytest.raises(ValueError, match="No audio files"):
            calculator.calculate_stats([])

    def test_calculate_stats_with_missing_file_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test that missing file raises error."""
        calculator = AudioStatsCalculator()
        missing_file = tmp_path / "missing.wav"

        with pytest.raises(FileNotFoundError):
            calculator.calculate_stats([missing_file])

    def test_save_stats_to_json(self, tmp_path: Path) -> None:
        """Test saving stats to JSON file."""
        # Arrange
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()
        stats = calculator.calculate_stats([audio_file])

        output_path = tmp_path / "audio_norm_stats.json"

        # Act
        calculator.save_stats(stats, output_path)

        # Assert
        assert output_path.exists()

    def test_saved_stats_json_is_valid(self, tmp_path: Path) -> None:
        """Test that saved JSON can be loaded."""
        # Arrange
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()
        stats = calculator.calculate_stats([audio_file])

        output_path = tmp_path / "audio_norm_stats.json"
        calculator.save_stats(stats, output_path)

        # Act - Load and verify
        import json

        with open(output_path, encoding="utf-8") as f:
            loaded_stats = json.load(f)

        # Assert
        assert loaded_stats["mean"] == stats["mean"]
        assert loaded_stats["std"] == stats["std"]
        assert loaded_stats["min"] == stats["min"]
        assert loaded_stats["max"] == stats["max"]

    def test_stats_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Test that stats calculation is deterministic."""
        # Arrange
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()

        # Act - Calculate twice
        stats1 = calculator.calculate_stats([audio_file])
        stats2 = calculator.calculate_stats([audio_file])

        # Assert
        assert stats1["mean"] == stats2["mean"]
        assert stats1["std"] == stats2["std"]
        assert stats1["min"] == stats2["min"]
        assert stats1["max"] == stats2["max"]

    def test_stats_include_sample_count(self, tmp_path: Path) -> None:
        """Test that stats include total sample count."""
        # Arrange
        files = []
        for i in range(3):
            audio_file = tmp_path / f"test_{i}.wav"
            self._create_test_wav(audio_file, duration_ms=500, sample_rate=22050)
            files.append(audio_file)

        calculator = AudioStatsCalculator()

        # Act
        stats = calculator.calculate_stats(files)

        # Assert
        assert "sample_count" in stats
        assert stats["sample_count"] > 0

    def test_calculate_stats_validates_16bit_pcm(self, tmp_path: Path) -> None:
        """Test that calculator validates 16-bit PCM format."""
        # Arrange - Create valid file
        audio_file = tmp_path / "test.wav"
        self._create_test_wav(audio_file, duration_ms=1000, sample_rate=22050)

        calculator = AudioStatsCalculator()

        # Act - Should succeed for 16-bit PCM
        stats = calculator.calculate_stats([audio_file])

        # Assert
        assert stats is not None

    def test_calculate_stats_skips_corrupted_wav(self, tmp_path: Path) -> None:
        """Test that corrupted WAV files are skipped with a warning."""
        # Arrange - Create one valid and one corrupted WAV
        good_file = tmp_path / "good.wav"
        self._create_test_wav(good_file, duration_ms=1000, sample_rate=22050)

        bad_file = tmp_path / "bad.wav"
        # Write a RIFF header with invalid size so wave module can't parse chunks
        bad_file.write_bytes(
            b"RIFF" + (8).to_bytes(4, "little") + b"WAVE" + b"\x00" * 100
        )

        calculator = AudioStatsCalculator()

        # Act - Should succeed using only the good file
        stats = calculator.calculate_stats([good_file, bad_file])

        # Assert
        assert stats is not None
        assert stats["sample_count"] > 0

    def test_calculate_stats_raises_if_all_files_corrupted(
        self, tmp_path: Path
    ) -> None:
        """Test that an error is raised when all files are corrupted."""
        # Arrange
        bad_file = tmp_path / "bad.wav"
        bad_file.write_bytes(
            b"RIFF" + (8).to_bytes(4, "little") + b"WAVE" + b"\x00" * 100
        )

        calculator = AudioStatsCalculator()

        # Act & Assert
        with pytest.raises(ValueError, match="No valid audio files found"):
            calculator.calculate_stats([bad_file])

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
