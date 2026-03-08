"""Unit tests for preprocess_japanese_dataset use case.

Following TDD: These tests are written BEFORE implementation.
Tests the application layer orchestration for Piper preprocessing.
"""

import json
import wave
from pathlib import Path

import numpy as np
import pytest

from piper_voice.application.preprocess_japanese_dataset import (
    PreprocessConfig,
    PreprocessResult,
    preprocess_japanese_dataset,
)


class TestPreprocessConfig:
    """Tests for PreprocessConfig value object."""

    def test_config_creation(self) -> None:
        """Test creating PreprocessConfig with valid paths."""
        config = PreprocessConfig(
            input_metadata=Path("metadata_phonemes.csv"),
            phoneme_map_path=Path("phoneme_map.json"),
            audio_dir=Path("wav"),
            output_dir=Path("training"),
            sample_rate=22050,
        )

        assert config.input_metadata == Path("metadata_phonemes.csv")
        assert config.phoneme_map_path == Path("phoneme_map.json")
        assert config.audio_dir == Path("wav")
        assert config.output_dir == Path("training")
        assert config.sample_rate == 22050


class TestPreprocessJapaneseDataset:
    """Tests for preprocess_japanese_dataset use case."""

    def test_preprocess_simple_dataset(self, tmp_path: Path) -> None:
        """Test preprocessing a simple dataset."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert
        assert result.success is True
        assert result.total_samples == 2

    def test_preprocess_creates_all_output_files(self, tmp_path: Path) -> None:
        """Test that preprocessing creates all required output files."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert - Check all output files exist
        assert result.dataset_jsonl.exists()
        assert result.config_json.exists()
        assert result.audio_stats_json.exists()

    def test_preprocess_validates_input_metadata_exists(self, tmp_path: Path) -> None:
        """Test that preprocessing validates input metadata exists."""
        # Arrange - Missing metadata
        config = PreprocessConfig(
            input_metadata=tmp_path / "missing.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Input metadata not found"):
            preprocess_japanese_dataset(config)

    def test_preprocess_validates_phoneme_map_exists(self, tmp_path: Path) -> None:
        """Test that preprocessing validates phoneme map exists."""
        # Arrange
        metadata = tmp_path / "metadata_phonemes.csv"
        metadata.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        config = PreprocessConfig(
            input_metadata=metadata,
            phoneme_map_path=tmp_path / "missing.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Phoneme map not found"):
            preprocess_japanese_dataset(config)

    def test_preprocess_validates_audio_dir_exists(self, tmp_path: Path) -> None:
        """Test that preprocessing validates audio directory exists."""
        # Arrange
        metadata = tmp_path / "metadata_phonemes.csv"
        metadata.write_text("audio_001.wav|0 1 2\n", encoding="utf-8")

        phoneme_map = tmp_path / "phoneme_map.json"
        phoneme_map.write_text('{"phonemes": {"あ": 0}}', encoding="utf-8")

        config = PreprocessConfig(
            input_metadata=metadata,
            phoneme_map_path=phoneme_map,
            audio_dir=tmp_path / "missing_wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Audio directory not found"):
            preprocess_japanese_dataset(config)

    def test_preprocess_result_contains_statistics(self, tmp_path: Path) -> None:
        """Test that result contains preprocessing statistics."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=5)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert
        assert result.total_samples == 5
        assert result.phoneme_count > 0

    def test_preprocess_creates_valid_dataset_jsonl(self, tmp_path: Path) -> None:
        """Test that dataset.jsonl is valid and loadable."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=3)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert - Load and verify JSONL
        lines = result.dataset_jsonl.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        for line in lines:
            entry = json.loads(line)
            assert "audio_file" in entry
            assert "phoneme_ids" in entry

    def test_preprocess_creates_valid_config_json(self, tmp_path: Path) -> None:
        """Test that config.json is valid Piper config."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert - Load and verify config
        with open(result.config_json, encoding="utf-8") as f:
            config_data = json.load(f)

        assert "num_symbols" in config_data
        assert "custom_phonemes" in config_data
        assert config_data["custom_phonemes"] is True
        assert "audio" in config_data
        assert config_data["audio"]["sample_rate"] == 22050

    def test_preprocess_creates_valid_audio_stats_json(self, tmp_path: Path) -> None:
        """Test that audio_norm_stats.json is valid."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert - Load and verify stats
        with open(result.audio_stats_json, encoding="utf-8") as f:
            stats = json.load(f)

        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_preprocess_with_16khz_sample_rate(self, tmp_path: Path) -> None:
        """Test preprocessing with 16000 Hz sample rate."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2, sample_rate=16000)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=16000,
        )

        # Act
        result = preprocess_japanese_dataset(config)

        # Assert
        assert result.success is True

        # Verify config has correct sample rate
        with open(result.config_json, encoding="utf-8") as f:
            config_data = json.load(f)
        assert config_data["audio"]["sample_rate"] == 16000

    def test_preprocess_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Test that preprocessing is deterministic."""
        # Arrange
        self._setup_test_dataset(tmp_path, num_samples=2)

        config = PreprocessConfig(
            input_metadata=tmp_path / "metadata_phonemes.csv",
            phoneme_map_path=tmp_path / "phoneme_map.json",
            audio_dir=tmp_path / "wav",
            output_dir=tmp_path / "training",
            sample_rate=22050,
        )

        # Act - Run twice
        result1 = preprocess_japanese_dataset(config)

        # Clear outputs
        result1.dataset_jsonl.unlink()
        result1.config_json.unlink()
        result1.audio_stats_json.unlink()

        result2 = preprocess_japanese_dataset(config)

        # Assert - Results should be identical
        assert result1.total_samples == result2.total_samples
        assert result1.phoneme_count == result2.phoneme_count

    def test_preprocess_result_dataclass(self) -> None:
        """Test PreprocessResult dataclass structure."""
        result = PreprocessResult(
            success=True,
            total_samples=100,
            skipped_samples=0,
            phoneme_count=95,
            dataset_jsonl=Path("dataset.jsonl"),
            config_json=Path("config.json"),
            audio_stats_json=Path("audio_norm_stats.json"),
            corrupted_files=[],
        )

        assert result.success is True
        assert result.total_samples == 100
        assert result.skipped_samples == 0
        assert result.phoneme_count == 95
        assert result.corrupted_files == []

    # Helper methods

    def _setup_test_dataset(
        self, tmp_path: Path, num_samples: int, sample_rate: int = 22050
    ) -> None:
        """Setup test dataset with audio files, metadata, and phoneme map."""
        # Create audio directory
        audio_dir = tmp_path / "wav"
        audio_dir.mkdir()

        # Create test audio files
        for i in range(num_samples):
            audio_file = audio_dir / f"audio_{i:03d}.wav"
            self._create_test_wav(audio_file, duration_ms=500, sample_rate=sample_rate)

        # Create metadata_phonemes.csv
        metadata_lines = [
            f"audio_{i:03d}.wav|{i} {i+1} {i+2}\n" for i in range(num_samples)
        ]
        metadata = tmp_path / "metadata_phonemes.csv"
        metadata.write_text("".join(metadata_lines), encoding="utf-8")

        # Create phoneme_map.json with real hiragana characters
        # Generate enough hiragana for the test
        hiragana_chars = "あいうえおかきくけこさしすせそたちつてと"
        phonemes = {char: i for i, char in enumerate(hiragana_chars[: num_samples + 3])}
        phoneme_map = tmp_path / "phoneme_map.json"
        phoneme_map.write_text(
            json.dumps({"phonemes": phonemes}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _create_test_wav(
        self, path: Path, duration_ms: int, sample_rate: int
    ) -> None:
        """Create a test WAV file."""
        num_samples = int(sample_rate * duration_ms / 1000)
        frequency = 440.0
        samples = np.sin(2 * np.pi * frequency * np.arange(num_samples) / sample_rate)
        samples_int16 = (samples * 32767).astype(np.int16)

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_int16.tobytes())
