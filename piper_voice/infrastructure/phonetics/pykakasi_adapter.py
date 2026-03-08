"""Pykakasi adapter for kanji-to-hiragana conversion.

This module implements the KanjiConverterPort using the pykakasi library
to convert Japanese text (kanji + kana) to pure hiragana.
"""

import pykakasi

from piper_voice.core.value_objects import HiraganaText


class PykakasiAdapter:
    """Adapter for pykakasi library.

    Implements KanjiConverterPort interface for Japanese text conversion.
    """

    def __init__(self) -> None:
        """Initialize pykakasi converter."""
        self.kakasi = pykakasi.kakasi()  # type: ignore[no-untyped-call]

    def convert_to_hiragana(self, text: str) -> HiraganaText:
        """Convert Japanese text to pure hiragana.

        Args:
            text: Japanese text (may contain kanji, hiragana, katakana)

        Returns:
            HiraganaText value object

        Raises:
            ValueError: If conversion fails or text is empty
        """
        # Check for empty input
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        # Convert using pykakasi
        result = self.kakasi.convert(text)

        # Extract hiragana from result
        # pykakasi returns list of dicts with 'hira' key
        hiragana_parts = [item['hira'] for item in result]
        hiragana_text = ''.join(hiragana_parts)

        # Return as HiraganaText (will validate)
        return HiraganaText(hiragana_text)
