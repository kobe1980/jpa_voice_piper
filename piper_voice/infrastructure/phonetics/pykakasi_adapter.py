"""Pykakasi adapter for kanji-to-hiragana conversion.

This module implements the KanjiConverterPort using the pykakasi library
to convert Japanese text (kanji + kana) to pure hiragana.

Includes a pre-processing step to normalize characters that pykakasi
cannot handle (fullwidth digits, Latin characters, etc.).
"""

import pykakasi

from piper_voice.core.value_objects import HiraganaText
from piper_voice.infrastructure.phonetics.text_normalizer import (
    normalize_japanese_text,
)


class PykakasiAdapter:
    """Adapter for pykakasi library.

    Implements KanjiConverterPort interface for Japanese text conversion.
    Pre-processes text to handle characters pykakasi cannot convert
    (digits, Latin letters) before running kanji→hiragana conversion.
    """

    def __init__(self) -> None:
        """Initialize pykakasi converter."""
        self.kakasi = pykakasi.kakasi()  # type: ignore[no-untyped-call]

    def convert_to_hiragana(self, text: str) -> HiraganaText:
        """Convert Japanese text to pure hiragana.

        Args:
            text: Japanese text (may contain kanji, hiragana, katakana,
                  digits, or Latin characters)

        Returns:
            HiraganaText value object

        Raises:
            ValueError: If conversion fails or text is empty
        """
        # Check for empty input
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        # Pre-process: normalize digits, Latin chars, fullwidth forms
        text = normalize_japanese_text(text)

        # Convert using pykakasi
        result = self.kakasi.convert(text)

        # Extract hiragana from result
        # pykakasi returns list of dicts with 'hira' key
        hiragana_parts = [item['hira'] for item in result]
        hiragana_text = ''.join(hiragana_parts)

        # Return as HiraganaText (will validate)
        return HiraganaText(hiragana_text)
