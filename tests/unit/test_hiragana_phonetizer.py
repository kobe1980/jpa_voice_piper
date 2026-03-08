"""Unit tests for HiraganaPhonetizer.

Following TDD: These tests are written BEFORE implementation.
Tests the hiragana phonetizer adapter that converts hiragana to phoneme IDs.
"""

import pytest

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText
from piper_voice.infrastructure.phonetics.hiragana_phonetizer import HiraganaPhonetizer


class TestHiraganaPhonetizer:
    """Tests for HiraganaPhonetizer."""

    def test_phonetizer_creation_with_phoneme_map(self) -> None:
        """Test creating HiraganaPhonetizer with PhonemeMap."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        assert phonetizer is not None

    def test_phonemize_simple_hiragana(self) -> None:
        """Test phonemizing simple hiragana text."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")
        phoneme_map.add_phoneme("う")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        text = HiraganaText("あいう")
        sequence = phonetizer.phonemize(text)

        assert sequence.ids == [0, 1, 2]

    def test_phonemize_with_spaces(self) -> None:
        """Test that spaces are ignored during phonemization."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        text = HiraganaText("あ い")
        sequence = phonetizer.phonemize(text)

        # Spaces should not be in sequence
        assert sequence.ids == [0, 1]

    def test_phonemize_with_punctuation(self) -> None:
        """Test phonemizing with Japanese punctuation."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("、")
        phoneme_map.add_phoneme("。")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        text = HiraganaText("あ、。")
        sequence = phonetizer.phonemize(text)

        assert sequence.ids == [0, 1, 2]

    def test_phonemize_raises_for_unknown_character(self) -> None:
        """Test that unknown character raises KeyError with helpful message."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        text = HiraganaText("あい")  # "い" not in map

        with pytest.raises(KeyError, match="Phoneme not found"):
            phonetizer.phonemize(text)

    def test_phonemize_long_text(self) -> None:
        """Test phonemizing long text."""
        # Build map from long text
        long_hiragana = "これはながいてきすとです" * 10
        texts = [HiraganaText(long_hiragana)]
        phoneme_map = PhonemeMap.build_from_texts(texts)

        phonetizer = HiraganaPhonetizer(phoneme_map)

        result = phonetizer.phonemize(HiraganaText(long_hiragana))

        assert len(result) > 100

    def test_phonemize_all_hiragana_characters(self) -> None:
        """Test that all basic hiragana can be phonemized."""
        # Basic hiragana: あいうえお...
        basic_hiragana = "あいうえおかきくけこさしすせそたちつてと"

        # Build map
        phoneme_map = PhonemeMap.build_from_texts([HiraganaText(basic_hiragana)])

        phonetizer = HiraganaPhonetizer(phoneme_map)

        result = phonetizer.phonemize(HiraganaText(basic_hiragana))

        # Should have same length as input (20 characters)
        assert len(result) == len(basic_hiragana)

    def test_phonetizer_is_reusable(self) -> None:
        """Test that phonetizer can be used multiple times."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")
        phoneme_map.add_phoneme("い")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        result1 = phonetizer.phonemize(HiraganaText("あ"))
        result2 = phonetizer.phonemize(HiraganaText("い"))

        assert result1.ids == [0]
        assert result2.ids == [1]

    def test_phonemize_text_with_only_space_character(self) -> None:
        """Test that text with spaces returns only non-space phonemes."""
        phoneme_map = PhonemeMap()
        phoneme_map.add_phoneme("あ")

        phonetizer = HiraganaPhonetizer(phoneme_map)

        # Text with spaces around character
        text = HiraganaText(" あ ")

        # Spaces are removed, only "あ" remains
        result = phonetizer.phonemize(text)
        assert result.ids == [0]
