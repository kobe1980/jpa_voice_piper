"""Unit tests for phoneme value objects.

Following TDD: These tests are written BEFORE implementation.
Tests the phoneme-related value objects for Japanese phonetization.
"""

import pytest

from piper_voice.core.value_objects import HiraganaText, Phoneme, PhonemeSequence


class TestPhoneme:
    """Tests for Phoneme value object."""

    def test_phoneme_creation_with_valid_data(self) -> None:
        """Test creating phoneme with valid character and ID."""
        phoneme = Phoneme(character="あ", id=0)

        assert phoneme.character == "あ"
        assert phoneme.id == 0

    def test_phoneme_is_immutable(self) -> None:
        """Test that phoneme is immutable (frozen dataclass)."""
        phoneme = Phoneme(character="い", id=1)

        with pytest.raises(AttributeError):
            phoneme.character = "う"  # type: ignore

    def test_phoneme_rejects_empty_character(self) -> None:
        """Test that empty character raises ValueError."""
        with pytest.raises(ValueError, match="character cannot be empty"):
            Phoneme(character="", id=0)

    def test_phoneme_rejects_negative_id(self) -> None:
        """Test that negative ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be non-negative"):
            Phoneme(character="あ", id=-1)

    def test_phoneme_rejects_multi_character_string(self) -> None:
        """Test that multi-character string raises ValueError."""
        with pytest.raises(ValueError, match="must be exactly 1 character"):
            Phoneme(character="あい", id=0)

    def test_phoneme_equality(self) -> None:
        """Test that phonemes with same data are equal."""
        phoneme1 = Phoneme(character="あ", id=0)
        phoneme2 = Phoneme(character="あ", id=0)

        assert phoneme1 == phoneme2

    def test_phoneme_inequality_different_character(self) -> None:
        """Test that phonemes with different characters are not equal."""
        phoneme1 = Phoneme(character="あ", id=0)
        phoneme2 = Phoneme(character="い", id=0)

        assert phoneme1 != phoneme2

    def test_phoneme_inequality_different_id(self) -> None:
        """Test that phonemes with different IDs are not equal."""
        phoneme1 = Phoneme(character="あ", id=0)
        phoneme2 = Phoneme(character="あ", id=1)

        assert phoneme1 != phoneme2


class TestHiraganaText:
    """Tests for HiraganaText value object."""

    def test_hiragana_text_creation_with_valid_hiragana(self) -> None:
        """Test creating HiraganaText with valid hiragana string."""
        text = HiraganaText("これはてすとです")

        assert text.value == "これはてすとです"

    def test_hiragana_text_allows_spaces(self) -> None:
        """Test that spaces are allowed in hiragana text."""
        text = HiraganaText("これは てすと です")

        assert text.value == "これは てすと です"

    def test_hiragana_text_allows_punctuation(self) -> None:
        """Test that Japanese punctuation is allowed."""
        text = HiraganaText("これは、てすとです。")

        assert "これは、てすとです。" in text.value

    def test_hiragana_text_is_immutable(self) -> None:
        """Test that HiraganaText is immutable."""
        text = HiraganaText("てすと")

        with pytest.raises(AttributeError):
            text.value = "あたらしい"  # type: ignore

    def test_hiragana_text_rejects_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            HiraganaText("")

    def test_hiragana_text_rejects_whitespace_only(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            HiraganaText("   \t\n  ")

    def test_hiragana_text_rejects_kanji(self) -> None:
        """Test that kanji characters raise ValueError."""
        with pytest.raises(ValueError, match="contains non-hiragana characters"):
            HiraganaText("日本語")

    def test_hiragana_text_rejects_katakana(self) -> None:
        """Test that katakana characters raise ValueError."""
        with pytest.raises(ValueError, match="contains non-hiragana characters"):
            HiraganaText("テスト")

    def test_hiragana_text_rejects_latin_characters(self) -> None:
        """Test that latin characters raise ValueError."""
        with pytest.raises(ValueError, match="contains non-hiragana characters"):
            HiraganaText("test")

    def test_hiragana_text_rejects_numbers(self) -> None:
        """Test that numbers raise ValueError."""
        with pytest.raises(ValueError, match="contains non-hiragana characters"):
            HiraganaText("123")

    def test_hiragana_text_rejects_suspicious_characters(self) -> None:
        """Test that suspicious characters raise ValueError (security)."""
        with pytest.raises(ValueError, match="contains suspicious characters"):
            HiraganaText("あ<script>")

    def test_hiragana_text_enforces_max_length(self) -> None:
        """Test that text exceeding max length raises ValueError."""
        long_text = "あ" * 501  # Max is 500

        with pytest.raises(ValueError, match="exceeds maximum length"):
            HiraganaText(long_text)

    def test_hiragana_text_equality(self) -> None:
        """Test that HiraganaText with same value are equal."""
        text1 = HiraganaText("てすと")
        text2 = HiraganaText("てすと")

        assert text1 == text2


class TestPhonemeSequence:
    """Tests for PhonemeSequence value object."""

    def test_phoneme_sequence_creation_with_valid_ids(self) -> None:
        """Test creating PhonemeSequence with valid phoneme IDs."""
        sequence = PhonemeSequence([0, 1, 2, 3])

        assert sequence.ids == [0, 1, 2, 3]

    def test_phoneme_sequence_is_immutable(self) -> None:
        """Test that PhonemeSequence is immutable."""
        sequence = PhonemeSequence([0, 1, 2])

        with pytest.raises(AttributeError):
            sequence.ids = [3, 4, 5]  # type: ignore

    def test_phoneme_sequence_rejects_empty_list(self) -> None:
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PhonemeSequence([])

    def test_phoneme_sequence_rejects_negative_ids(self) -> None:
        """Test that negative IDs raise ValueError."""
        with pytest.raises(ValueError, match="All phoneme IDs must be non-negative"):
            PhonemeSequence([0, 1, -1, 3])

    def test_phoneme_sequence_to_string_space_separated(self) -> None:
        """Test that to_string returns space-separated IDs."""
        sequence = PhonemeSequence([0, 1, 2, 3])

        assert sequence.to_string() == "0 1 2 3"

    def test_phoneme_sequence_to_string_single_id(self) -> None:
        """Test to_string with single phoneme ID."""
        sequence = PhonemeSequence([42])

        assert sequence.to_string() == "42"

    def test_phoneme_sequence_from_string_valid_input(self) -> None:
        """Test creating PhonemeSequence from space-separated string."""
        sequence = PhonemeSequence.from_string("0 1 2 3")

        assert sequence.ids == [0, 1, 2, 3]

    def test_phoneme_sequence_from_string_single_id(self) -> None:
        """Test from_string with single ID."""
        sequence = PhonemeSequence.from_string("42")

        assert sequence.ids == [42]

    def test_phoneme_sequence_from_string_rejects_empty(self) -> None:
        """Test that from_string rejects empty string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PhonemeSequence.from_string("")

    def test_phoneme_sequence_from_string_rejects_non_numeric(self) -> None:
        """Test that from_string rejects non-numeric input."""
        with pytest.raises(ValueError, match="Invalid phoneme ID"):
            PhonemeSequence.from_string("0 1 abc 3")

    def test_phoneme_sequence_from_string_rejects_negative(self) -> None:
        """Test that from_string rejects negative IDs."""
        with pytest.raises(ValueError, match="Invalid phoneme ID"):
            PhonemeSequence.from_string("0 1 -1 3")

    def test_phoneme_sequence_equality(self) -> None:
        """Test that PhonemeSequence with same IDs are equal."""
        seq1 = PhonemeSequence([0, 1, 2])
        seq2 = PhonemeSequence([0, 1, 2])

        assert seq1 == seq2

    def test_phoneme_sequence_inequality(self) -> None:
        """Test that PhonemeSequence with different IDs are not equal."""
        seq1 = PhonemeSequence([0, 1, 2])
        seq2 = PhonemeSequence([0, 1, 3])

        assert seq1 != seq2

    def test_phoneme_sequence_length(self) -> None:
        """Test that __len__ returns number of phonemes."""
        sequence = PhonemeSequence([0, 1, 2, 3, 4])

        assert len(sequence) == 5
