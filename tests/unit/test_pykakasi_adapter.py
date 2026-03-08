"""Unit tests for PykakasiAdapter.

Following TDD: These tests are written BEFORE implementation.
Tests the pykakasi adapter for kanji-to-hiragana conversion.
"""

import pytest

from piper_voice.core.value_objects import HiraganaText
from piper_voice.infrastructure.phonetics.pykakasi_adapter import PykakasiAdapter


class TestPykakasiAdapter:
    """Tests for PykakasiAdapter."""

    def test_adapter_creation(self) -> None:
        """Test creating PykakasiAdapter."""
        adapter = PykakasiAdapter()

        assert adapter is not None

    def test_convert_pure_hiragana_unchanged(self) -> None:
        """Test that pure hiragana text remains unchanged."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("これはてすとです")

        assert isinstance(result, HiraganaText)
        assert result.value == "これはてすとです"

    def test_convert_kanji_to_hiragana(self) -> None:
        """Test converting kanji to hiragana."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("日本語")

        assert isinstance(result, HiraganaText)
        # "日本語" should become "にほんご"
        assert result.value == "にほんご"

    def test_convert_mixed_kanji_hiragana(self) -> None:
        """Test converting mixed kanji and hiragana."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("今日はいい天気です")

        assert isinstance(result, HiraganaText)
        # "今日" → "こんにち" or "きょう" (multiple readings)
        # "天気" → "てんき"
        assert "てんき" in result.value
        assert "です" in result.value

    def test_convert_katakana_to_hiragana(self) -> None:
        """Test converting katakana to hiragana."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("テスト")

        assert isinstance(result, HiraganaText)
        # "テスト" should become "てすと"
        assert result.value == "てすと"

    def test_convert_with_spaces(self) -> None:
        """Test that spaces are preserved."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("日本 語")

        assert isinstance(result, HiraganaText)
        assert " " in result.value

    def test_convert_with_japanese_punctuation(self) -> None:
        """Test that Japanese punctuation is preserved."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("こんにちは、日本。")

        assert isinstance(result, HiraganaText)
        assert "、" in result.value
        assert "。" in result.value

    def test_convert_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        adapter = PykakasiAdapter()

        # HiraganaText constructor will raise ValueError for empty string
        with pytest.raises(ValueError, match="cannot be empty"):
            adapter.convert_to_hiragana("")

    def test_convert_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        adapter = PykakasiAdapter()

        with pytest.raises(ValueError, match="cannot be empty"):
            adapter.convert_to_hiragana("   \t\n  ")

    def test_convert_numbers_rejected(self) -> None:
        """Test that numbers are rejected (can't convert to valid hiragana)."""
        adapter = PykakasiAdapter()

        # pykakasi keeps numbers as-is, which are not valid hiragana
        # HiraganaText validation should reject this
        with pytest.raises(ValueError, match="non-hiragana characters"):
            adapter.convert_to_hiragana("123")

    def test_convert_latin_characters_handled(self) -> None:
        """Test that latin characters are handled."""
        adapter = PykakasiAdapter()

        # Latin characters can't be converted to hiragana
        # pykakasi might keep them or convert them
        # We test that it doesn't crash
        try:
            result = adapter.convert_to_hiragana("test")
            assert isinstance(result, HiraganaText)
        except ValueError:
            # It's also acceptable to reject latin-only text
            pass

    def test_convert_long_text(self) -> None:
        """Test converting long text."""
        adapter = PykakasiAdapter()

        long_text = "これは非常に長いテキストです。" * 10

        result = adapter.convert_to_hiragana(long_text)

        assert isinstance(result, HiraganaText)
        assert len(result.value) > 0

    def test_convert_common_japanese_sentence(self) -> None:
        """Test converting a common Japanese sentence."""
        adapter = PykakasiAdapter()

        result = adapter.convert_to_hiragana("私は学生です")

        assert isinstance(result, HiraganaText)
        # "私" → "わたし", "学生" → "がくせい"
        assert "わたし" in result.value or "わたくし" in result.value
        assert "がくせい" in result.value
        assert "です" in result.value

    def test_adapter_is_reusable(self) -> None:
        """Test that adapter can be used multiple times."""
        adapter = PykakasiAdapter()

        result1 = adapter.convert_to_hiragana("日本")
        result2 = adapter.convert_to_hiragana("語")

        # "日本" can be "にほん" or "にっぽん" (both valid readings)
        assert result1.value in ("にほん", "にっぽん")
        assert result2.value == "ご"
