"""Unit tests for PhonemeMap entity.

Following TDD: These tests are written BEFORE implementation.
Tests the PhonemeMap entity for managing hiragana-to-phoneme-ID mappings.
"""

import json
from pathlib import Path

import pytest

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText


class TestPhonemeMap:
    """Tests for PhonemeMap entity."""

    def test_phoneme_map_creation_empty(self) -> None:
        """Test creating empty PhonemeMap."""
        phoneme_map = PhonemeMap()

        assert len(phoneme_map.phonemes) == 0

    def test_phoneme_map_add_phoneme(self) -> None:
        """Test adding phoneme to map."""
        phoneme_map = PhonemeMap()

        phoneme_map.add_phoneme("あ")

        assert len(phoneme_map.phonemes) == 1
        assert phoneme_map.get_phoneme_id("あ") == 0

    def test_phoneme_map_add_multiple_phonemes(self) -> None:
        """Test adding multiple phonemes."""
        phoneme_map = PhonemeMap()

        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        assert len(phoneme_map.phonemes) == 3
        assert phoneme_map.get_phoneme_id("あ") == 0
        assert phoneme_map.get_phoneme_id("い") == 1
        assert phoneme_map.get_phoneme_id("う") == 2

    def test_phoneme_map_add_duplicate_phoneme_is_idempotent(self) -> None:
        """Test that adding same phoneme twice doesn't create duplicate."""
        phoneme_map = PhonemeMap()

        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("あ")  # Duplicate

        assert len(phoneme_map.phonemes) == 1
        assert phoneme_map.get_phoneme_id("あ") == 0

    def test_phoneme_map_get_phoneme_id_raises_for_unknown_character(self) -> None:
        """Test that getting ID for unknown character raises KeyError."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        with pytest.raises(KeyError, match="Phoneme not found"):
            phoneme_map.get_phoneme_id("え")

    def test_phoneme_map_get_phoneme_char(self) -> None:
        """Test getting phoneme character by ID."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        assert phoneme_map.get_phoneme_char(0) == "あ"
        assert phoneme_map.get_phoneme_char(1) == "い"

    def test_phoneme_map_get_phoneme_char_raises_for_invalid_id(self) -> None:
        """Test that getting char for invalid ID raises KeyError."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        with pytest.raises(KeyError, match="Phoneme ID not found"):
            phoneme_map.get_phoneme_char(99)

    def test_phoneme_map_has_phoneme(self) -> None:
        """Test checking if phoneme exists in map."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        assert phoneme_map.has_phoneme("あ")
        assert not phoneme_map.has_phoneme("え")

    def test_phoneme_map_phonemize_hiragana_text(self) -> None:
        """Test converting HiraganaText to PhonemeSequence."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        text = HiraganaText("あいう")
        sequence = phoneme_map.phonemize(text)

        assert sequence.ids == [0, 1, 2]

    def test_phoneme_map_phonemize_with_spaces(self) -> None:
        """Test phonemizing text with spaces (spaces are ignored)."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        text = HiraganaText("あ い")
        sequence = phoneme_map.phonemize(text)

        # Space should not be in phoneme sequence
        assert sequence.ids == [0, 1]

    def test_phoneme_map_phonemize_with_punctuation(self) -> None:
        """Test phonemizing text with punctuation (punctuation handled)."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("、")
        phoneme_map.add_phoneme("。")

        text = HiraganaText("あ、。")
        sequence = phoneme_map.phonemize(text)

        assert sequence.ids == [0, 1, 2]

    def test_phoneme_map_phonemize_raises_for_unknown_character(self) -> None:
        """Test that phonemizing with unknown character raises KeyError."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        text = HiraganaText("あい")  # "い" not in map

        with pytest.raises(KeyError, match="Phoneme not found"):
            phoneme_map.phonemize(text)

    def test_phoneme_map_build_from_texts(self) -> None:
        """Test factory method to build map from multiple texts."""
        texts = [
            HiraganaText("あいう"),
            HiraganaText("いうえ"),
            HiraganaText("うえお"),
        ]

        phoneme_map = PhonemeMap.build_from_texts(texts)

        # Should have 5 unique phonemes: あいうえお
        assert len(phoneme_map.phonemes) == 5
        assert phoneme_map.has_phoneme("あ")
        assert phoneme_map.has_phoneme("い")
        assert phoneme_map.has_phoneme("う")
        assert phoneme_map.has_phoneme("え")
        assert phoneme_map.has_phoneme("お")

    def test_phoneme_map_build_from_texts_deterministic_ordering(self) -> None:
        """Test that build_from_texts produces deterministic phoneme IDs."""
        texts = [
            HiraganaText("おえういあ"),  # Unsorted
        ]

        phoneme_map = PhonemeMap.build_from_texts(texts)

        # IDs should be assigned in sorted order
        assert phoneme_map.get_phoneme_id("あ") < phoneme_map.get_phoneme_id("い")
        assert phoneme_map.get_phoneme_id("い") < phoneme_map.get_phoneme_id("う")
        assert phoneme_map.get_phoneme_id("う") < phoneme_map.get_phoneme_id("え")
        assert phoneme_map.get_phoneme_id("え") < phoneme_map.get_phoneme_id("お")

    def test_phoneme_map_build_from_texts_ignores_spaces(self) -> None:
        """Test that build_from_texts ignores spaces."""
        texts = [
            HiraganaText("あ い う"),
        ]

        phoneme_map = PhonemeMap.build_from_texts(texts)

        # Should have 3 phonemes (space not included)
        assert len(phoneme_map.phonemes) == 3
        assert not phoneme_map.has_phoneme(" ")

    def test_phoneme_map_enforces_max_phonemes_limit(self) -> None:
        """Test that exceeding max phonemes raises ValueError."""
        phoneme_map = PhonemeMap(max_phonemes=3)

        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        # Adding 4th should fail
        with pytest.raises(ValueError, match="Maximum number of phonemes"):
            phoneme_map.add_phoneme("え")

    def test_phoneme_map_to_dict(self) -> None:
        """Test converting PhonemeMap to dictionary."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        data = phoneme_map.to_dict()

        assert "phonemes" in data
        assert len(data["phonemes"]) == 2
        assert data["phonemes"]["あ"] == 0
        assert data["phonemes"]["い"] == 1

    def test_phoneme_map_from_dict(self) -> None:
        """Test creating PhonemeMap from dictionary."""
        data = {
            "phonemes": {
                "あ": 0,
                "い": 1,
                "う": 2,
            }
        }

        phoneme_map = PhonemeMap.from_dict(data)

        assert len(phoneme_map.phonemes) == 3
        assert phoneme_map.get_phoneme_id("あ") == 0
        assert phoneme_map.get_phoneme_id("い") == 1
        assert phoneme_map.get_phoneme_id("う") == 2

    def test_phoneme_map_save_to_json(self, tmp_path: Path) -> None:
        """Test saving PhonemeMap to JSON file."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        json_file = tmp_path / "phoneme_map.json"
        phoneme_map.save_to_json(json_file)

        assert json_file.exists()

        # Check file contents
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "phonemes" in data
        assert data["phonemes"]["あ"] == 0
        assert data["phonemes"]["い"] == 1

    def test_phoneme_map_load_from_json(self, tmp_path: Path) -> None:
        """Test loading PhonemeMap from JSON file."""
        json_file = tmp_path / "phoneme_map.json"

        # Create test JSON file
        data = {
            "phonemes": {
                "あ": 0,
                "い": 1,
                "う": 2,
            }
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Load
        phoneme_map = PhonemeMap.load_from_json(json_file)

        assert len(phoneme_map.phonemes) == 3
        assert phoneme_map.get_phoneme_id("あ") == 0
        assert phoneme_map.get_phoneme_id("い") == 1
        assert phoneme_map.get_phoneme_id("う") == 2

    def test_phoneme_map_size(self) -> None:
        """Test __len__ returns number of phonemes."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        assert len(phoneme_map) == 3
