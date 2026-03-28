"""Unit tests for Japanese text normalizer.

Tests the pre-processing step that converts characters pykakasi
cannot handle (digits, Latin characters, etc.) to hiragana readings.
"""

import pytest

from piper_voice.infrastructure.phonetics.text_normalizer import (
    _number_to_hiragana,
    normalize_japanese_text,
)


class TestNumberToHiragana:
    """Tests for integer-to-hiragana conversion."""

    def test_zero(self) -> None:
        assert _number_to_hiragana(0) == "ぜろ"

    def test_single_digits(self) -> None:
        assert _number_to_hiragana(1) == "いち"
        assert _number_to_hiragana(2) == "に"
        assert _number_to_hiragana(3) == "さん"
        assert _number_to_hiragana(4) == "よん"
        assert _number_to_hiragana(5) == "ご"
        assert _number_to_hiragana(6) == "ろく"
        assert _number_to_hiragana(7) == "なな"
        assert _number_to_hiragana(8) == "はち"
        assert _number_to_hiragana(9) == "きゅう"

    def test_tens(self) -> None:
        assert _number_to_hiragana(10) == "じゅう"
        assert _number_to_hiragana(20) == "にじゅう"
        assert _number_to_hiragana(11) == "じゅういち"
        assert _number_to_hiragana(42) == "よんじゅうに"
        assert _number_to_hiragana(99) == "きゅうじゅうきゅう"

    def test_hundreds(self) -> None:
        assert _number_to_hiragana(100) == "ひゃく"
        assert _number_to_hiragana(200) == "にひゃく"
        assert _number_to_hiragana(500) == "ごひゃく"

    def test_hundreds_rendaku(self) -> None:
        """Test special readings for 300, 600, 800."""
        assert _number_to_hiragana(300) == "さんびゃく"
        assert _number_to_hiragana(600) == "ろっぴゃく"
        assert _number_to_hiragana(800) == "はっぴゃく"

    def test_thousands(self) -> None:
        assert _number_to_hiragana(1000) == "せん"
        assert _number_to_hiragana(2000) == "にせん"
        assert _number_to_hiragana(5000) == "ごせん"

    def test_thousands_rendaku(self) -> None:
        """Test special readings for 3000, 8000."""
        assert _number_to_hiragana(3000) == "さんぜん"
        assert _number_to_hiragana(8000) == "はっせん"

    def test_ten_thousands(self) -> None:
        assert _number_to_hiragana(10000) == "いちまん"
        assert _number_to_hiragana(20000) == "にまん"
        assert _number_to_hiragana(50000) == "ごまん"

    def test_composite_numbers(self) -> None:
        assert _number_to_hiragana(1234) == "せんにひゃくさんじゅうよん"
        assert _number_to_hiragana(10500) == "いちまんごひゃく"


class TestNormalizeJapaneseText:
    """Tests for the full normalization pipeline."""

    def test_fullwidth_single_digit(self) -> None:
        """Test fullwidth digit normalization (the main failure case)."""
        result = normalize_japanese_text("１週間")
        assert result == "いち週間"

    def test_fullwidth_multi_digit(self) -> None:
        result = normalize_japanese_text("２０億円")
        assert result == "にじゅう億円"

    def test_fullwidth_digit_four(self) -> None:
        result = normalize_japanese_text("４大大会")
        assert result == "よん大大会"

    def test_halfwidth_digits(self) -> None:
        result = normalize_japanese_text("3時間")
        assert result == "さん時間"

    def test_decimal_number(self) -> None:
        result = normalize_japanese_text("３．５キロ")
        assert result == "さんてんごキロ"

    def test_latin_characters(self) -> None:
        result = normalize_japanese_text("CPUを使う")
        assert result == "しーぴーゆーを使う"

    def test_text_without_special_chars(self) -> None:
        """Test that pure kanji/kana text passes through unchanged."""
        text = "これはテストです"
        assert normalize_japanese_text(text) == text

    def test_mixed_text(self) -> None:
        """Test text with both digits and kanji."""
        result = normalize_japanese_text("１週間して、そのニュースは本当になった。")
        assert result == "いち週間して、そのニュースは本当になった。"

    def test_large_number(self) -> None:
        result = normalize_japanese_text("１０００人")
        assert result == "せん人"

    def test_empty_preserves_punctuation(self) -> None:
        """Test that Japanese punctuation is preserved."""
        result = normalize_japanese_text("「１」です。")
        assert result == "「いち」です。"

    def test_hyphen_between_numbers(self) -> None:
        """Test numbers separated by hyphen (converted to long vowel mark)."""
        result = normalize_japanese_text("１０-２０")
        assert result == "じゅうーにじゅう"

    def test_fullwidth_question_mark(self) -> None:
        """Test fullwidth ? is preserved as ？ after NFKC normalization."""
        result = normalize_japanese_text("本当？")
        assert result == "本当？"

    def test_halfwidth_question_mark(self) -> None:
        """Test halfwidth ? is converted to ？."""
        result = normalize_japanese_text("本当?")
        assert result == "本当？"

    def test_fullwidth_period(self) -> None:
        """Test fullwidth period ． is converted to 。 after NFKC."""
        result = normalize_japanese_text("です．")
        assert result == "です。"

    def test_halfwidth_period(self) -> None:
        """Test halfwidth period . is converted to 。."""
        result = normalize_japanese_text("です.")
        assert result == "です。"

    def test_exclamation_mark(self) -> None:
        """Test ! is converted to ！."""
        result = normalize_japanese_text("すごい!")
        assert result == "すごい！"

    def test_noma_expansion(self) -> None:
        """Test 々 (noma) kanji repetition mark is expanded."""
        result = normalize_japanese_text("人々")
        assert result == "人人"

    def test_noma_expansion_multiple(self) -> None:
        """Test multiple 々 are expanded correctly."""
        result = normalize_japanese_text("日々の人々")
        assert result == "日日の人人"

    def test_noma_at_start_preserved(self) -> None:
        """Test 々 at start of text (no preceding char) is kept as-is."""
        result = normalize_japanese_text("々テスト")
        assert result == "々テスト"

    def test_decimal_not_affected_by_punctuation_map(self) -> None:
        """Test that decimal points in numbers are handled before punctuation step."""
        result = normalize_japanese_text("３．５キロ")
        assert result == "さんてんごキロ"
