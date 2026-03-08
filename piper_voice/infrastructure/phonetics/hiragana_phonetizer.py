"""Hiragana phonetizer adapter.

This module implements the PhonetizerPort using PhonemeMap from the domain
to convert hiragana text to phoneme ID sequences.
"""

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText, PhonemeSequence


class HiraganaPhonetizer:
    """Adapter for hiragana-to-phoneme conversion.

    Implements PhonetizerPort interface using domain PhonemeMap.
    """

    def __init__(self, phoneme_map: PhonemeMap) -> None:
        """Initialize phonetizer with phoneme map.

        Args:
            phoneme_map: PhonemeMap entity with hiragana→ID mappings
        """
        self.phoneme_map = phoneme_map

    def phonemize(self, text: HiraganaText) -> PhonemeSequence:
        """Convert hiragana text to phoneme ID sequence.

        Args:
            text: Hiragana text to phonemize

        Returns:
            PhonemeSequence with phoneme IDs

        Raises:
            KeyError: If text contains character not in phoneme map
            ValueError: If phonemization produces empty sequence
        """
        # Delegate to domain PhonemeMap
        # PhonemeMap.phonemize handles space removal and validation
        try:
            return self.phoneme_map.phonemize(text)
        except KeyError as e:
            # Re-raise with more context
            raise KeyError(
                f"Phoneme not found for character in text: {text.value}"
            ) from e
