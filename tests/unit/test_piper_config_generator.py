"""Unit tests for PiperConfigGenerator.

Following TDD: These tests are written BEFORE implementation.
Tests the Piper config.json generation with custom phoneme mappings.
"""

from pathlib import Path

import pytest

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText
from piper_voice.infrastructure.piper.config_generator import PiperConfigGenerator


class TestPiperConfigGenerator:
    """Tests for PiperConfigGenerator."""

    def test_generator_creation(self) -> None:
        """Test creating PiperConfigGenerator."""
        generator = PiperConfigGenerator()
        assert generator is not None

    def test_generate_config_basic(self, tmp_path: Path) -> None:
        """Test generating basic Piper config."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        assert output_path.exists()

    def test_config_contains_audio_parameters(self, tmp_path: Path) -> None:
        """Test that config contains required Piper audio parameters."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert - Load and verify config
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "audio" in config
        assert config["audio"]["sample_rate"] == 22050
        assert "filter_length" in config["audio"]
        assert "hop_length" in config["audio"]
        assert "win_length" in config["audio"]
        assert "mel_channels" in config["audio"]

    def test_config_contains_phoneme_mappings(self, tmp_path: Path) -> None:
        """Test that config contains custom phoneme mappings."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "phonemes" in config
        assert config["phonemes"]["あ"] == 0
        assert config["phonemes"]["い"] == 1
        assert config["phonemes"]["う"] == 2

    def test_config_contains_num_symbols(self, tmp_path: Path) -> None:
        """Test that config contains correct num_symbols."""
        # Arrange
        phoneme_map = PhonemeMap()
        for char in "あいうえお":
            phoneme_map.add_phoneme(char)

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["num_symbols"] == 5

    def test_config_contains_custom_phonemes_flag(self, tmp_path: Path) -> None:
        """Test that config is flagged as using custom phonemes."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["custom_phonemes"] is True

    def test_config_contains_language_metadata(self, tmp_path: Path) -> None:
        """Test that config contains language metadata."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
            language="ja-jp",
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["language"] == "ja-jp"

    def test_generate_config_with_16khz_sample_rate(self, tmp_path: Path) -> None:
        """Test generating config with 16000 Hz sample rate."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=16000,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["audio"]["sample_rate"] == 16000

    def test_generate_config_rejects_invalid_sample_rate(self, tmp_path: Path) -> None:
        """Test that invalid sample rate raises error."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="Sample rate must be 16000 or 22050"):
            generator.generate_config(
                phoneme_map=phoneme_map,
                output_path=output_path,
                sample_rate=44100,  # Invalid
            )

    def test_generate_config_with_large_phoneme_map(self, tmp_path: Path) -> None:
        """Test generating config with realistic phoneme count (~100)."""
        # Arrange - Build map with comprehensive hiragana
        hiragana_text = (
            "あいうえおかきくけこさしすせそたちつてと"
            "なにぬねのはひふへほまみむめもやゆよ"
            "らりるれろわをんがぎぐげござじずぜぞ"
            "だぢづでどばびぶべぼぱぴぷぺぽ"
            "ぁぃぅぇぉっゃゅょゎ、。"
        )
        texts = [HiraganaText(hiragana_text)]
        phoneme_map = PhonemeMap.build_from_texts(texts)

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["num_symbols"] >= 80  # Realistic count
        assert len(config["phonemes"]) == config["num_symbols"]

    def test_generate_config_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that generator creates parent directory if needed."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "subdir" / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_config_json_is_pretty_printed(self, tmp_path: Path) -> None:
        """Test that config.json is human-readable (pretty-printed)."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert - Check for indentation
        content = output_path.read_text(encoding="utf-8")
        assert "  " in content  # Has indentation
        assert "\n" in content  # Has newlines

    def test_config_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Test that config generation is deterministic."""
        # Arrange
        phoneme_map = PhonemeMap()
        for char in "あいうえお":
            phoneme_map.add_phoneme(char)

        generator = PiperConfigGenerator()

        # Act - Generate twice
        path1 = tmp_path / "config1.json"
        path2 = tmp_path / "config2.json"

        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=path1,
            sample_rate=22050,
        )

        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=path2,
            sample_rate=22050,
        )

        # Assert - Configs should be identical
        content1 = path1.read_text(encoding="utf-8")
        content2 = path2.read_text(encoding="utf-8")
        assert content1 == content2

    def test_generate_config_with_empty_phoneme_map_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test that empty phoneme map raises error."""
        # Arrange
        phoneme_map = PhonemeMap()  # Empty
        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="PhonemeMap cannot be empty"):
            generator.generate_config(
                phoneme_map=phoneme_map,
                output_path=output_path,
                sample_rate=22050,
            )

    def test_config_contains_inference_parameters(self, tmp_path: Path) -> None:
        """Test that config contains inference parameters."""
        # Arrange
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        output_path = tmp_path / "config.json"
        generator = PiperConfigGenerator()

        # Act
        generator.generate_config(
            phoneme_map=phoneme_map,
            output_path=output_path,
            sample_rate=22050,
        )

        # Assert
        import json

        with open(output_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "inference" in config
        assert "noise_scale" in config["inference"]
        assert "length_scale" in config["inference"]
        assert "noise_w" in config["inference"]
