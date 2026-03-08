"""Unit tests for phonemize_japanese_corpus use case.

Following TDD: These tests are written BEFORE implementation.
Tests the application layer orchestration for Japanese phonemization.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from piper_voice.application.phonemize_japanese_corpus import (
    PhonemeCorpusConfig,
    phonemize_japanese_corpus,
)
from piper_voice.core.value_objects import HiraganaText


class TestPhonemeCorpusConfig:
    """Tests for PhonemeCorpusConfig value object."""

    def test_config_creation(self) -> None:
        """Test creating config with valid paths."""
        config = PhonemeCorpusConfig(
            input_metadata=Path("metadata.csv"),
            output_metadata=Path("metadata_phonemes.csv"),
            phoneme_map_output=Path("phoneme_map.json"),
        )

        assert config.input_metadata == Path("metadata.csv")
        assert config.output_metadata == Path("metadata_phonemes.csv")
        assert config.phoneme_map_output == Path("phoneme_map.json")


class TestPhonemizeJapaneseCorpus:
    """Tests for phonemize_japanese_corpus use case."""

    def test_phonemize_simple_corpus(self, tmp_path: Path) -> None:
        """Test phonemizing a simple corpus."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Create input metadata with Japanese text
        input_csv.write_text(
            "audio_001.wav|こんにちは\n" "audio_002.wav|ありがとう\n", encoding="utf-8"
        )

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        # Mock adapters
        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.side_effect = [
            HiraganaText("こんにちは"),
            HiraganaText("ありがとう"),
        ]

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert
        assert result.total_samples == 2
        assert result.successful == 2
        assert result.failed == 0
        assert output_csv.exists()
        assert phoneme_map_json.exists()

    def test_phonemize_with_kanji_conversion(self, tmp_path: Path) -> None:
        """Test phonemizing corpus with kanji that needs conversion."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Kanji text
        input_csv.write_text("audio_001.wav|日本語\n", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        # Mock kanji converter
        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.return_value = HiraganaText("にほんご")

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert
        assert result.successful == 1
        kanji_converter.convert_to_hiragana.assert_called_once_with("日本語")

    def test_phonemize_builds_phoneme_map(self, tmp_path: Path) -> None:
        """Test that phoneme map is built from all unique characters."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text(
            "audio_001.wav|あいう\n" "audio_002.wav|いうえ\n", encoding="utf-8"
        )

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.side_effect = [
            HiraganaText("あいう"),
            HiraganaText("いうえ"),
        ]

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - phoneme map should have 4 unique chars: あ, い, う, え
        assert result.phoneme_count == 4

    def test_phonemize_saves_output_files(self, tmp_path: Path) -> None:
        """Test that output files are created correctly."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text("audio_001.wav|あい\n", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.return_value = HiraganaText("あい")

        # Act
        phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - check output files exist
        assert output_csv.exists()
        assert phoneme_map_json.exists()

        # Check output CSV format (audio_file|phoneme_ids)
        output_content = output_csv.read_text(encoding="utf-8")
        assert "audio_001.wav|" in output_content
        assert " " in output_content  # Space-separated phoneme IDs

    def test_phonemize_handles_empty_corpus(self, tmp_path: Path) -> None:
        """Test handling empty corpus gracefully."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text("", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()

        # Act & Assert - should handle gracefully
        with pytest.raises(ValueError, match="No samples found"):
            phonemize_japanese_corpus(
                config=config,
                kanji_converter=kanji_converter,
            )

    def test_phonemize_handles_conversion_failure(self, tmp_path: Path) -> None:
        """Test handling when kanji conversion fails."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text(
            "audio_001.wav|こんにちは\n" "audio_002.wav|123\n",  # Numbers can't convert
            encoding="utf-8",
        )

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.side_effect = [
            HiraganaText("こんにちは"),
            ValueError("Cannot convert numbers to hiragana"),
        ]

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - should record failure but continue
        assert result.total_samples == 2
        assert result.successful == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_phonemize_respects_deterministic_ordering(self, tmp_path: Path) -> None:
        """Test that phoneme IDs are deterministic (sorted order)."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Characters in reverse order
        input_csv.write_text("audio_001.wav|えういあ\n", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.return_value = HiraganaText("えういあ")

        # Act
        phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - Load phoneme map and check ordering
        # Characters should be sorted: あ(0), い(1), う(2), え(3)
        # So "えういあ" → "3 2 1 0"
        output_content = output_csv.read_text(encoding="utf-8")
        assert "audio_001.wav|3 2 1 0\n" in output_content

    def test_phonemize_result_dataclass(self) -> None:
        """Test PhonemeResult dataclass structure."""
        from piper_voice.application.phonemize_japanese_corpus import PhonemeResult

        result = PhonemeResult(
            total_samples=10,
            successful=9,
            failed=1,
            phoneme_count=95,
            errors=["Sample 5 failed"],
        )

        assert result.total_samples == 10
        assert result.successful == 9
        assert result.failed == 1
        assert result.phoneme_count == 95
        assert len(result.errors) == 1

    def test_phonemize_handles_japanese_punctuation(self, tmp_path: Path) -> None:
        """Test handling Japanese punctuation in text."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text(
            "audio_001.wav|こんにちは、元気ですか。\n", encoding="utf-8"
        )

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.return_value = HiraganaText(
            "こんにちは、げんきですか。"
        )

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - should handle punctuation
        assert result.successful == 1

    def test_phonemize_large_corpus(self, tmp_path: Path) -> None:
        """Test phonemizing larger corpus (100 samples)."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Generate 100 samples
        lines = [f"audio_{i:03d}.wav|これはテストです\n" for i in range(100)]
        input_csv.write_text("".join(lines), encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = Mock()
        kanji_converter.convert_to_hiragana.return_value = HiraganaText(
            "これはてすとです"
        )

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert
        assert result.total_samples == 100
        assert result.successful == 100
        assert result.failed == 0
        assert kanji_converter.convert_to_hiragana.call_count == 100
