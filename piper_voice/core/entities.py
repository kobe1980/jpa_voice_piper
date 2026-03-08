"""Domain entities for Piper Voice dataset.

Entities have identity and lifecycle. They are mutable and defined by their ID.
The Voice entity is the aggregate root that maintains consistency across
related entities.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from piper_voice.core.value_objects import (
    AudioFormat,
    AudioQuality,
    Duration,
    HiraganaText,
    PhonemeSequence,
    SampleRate,
)
from piper_voice.core.value_objects import Phoneme as PhonemeValue


@dataclass
class Phoneme:
    """Phoneme entity.

    Represents a single phonetic unit with its symbol, ID, and language.
    """

    symbol: str
    id: int
    language: str

    def __eq__(self, other: object) -> bool:
        """Phonemes are equal if they have same symbol and language."""
        if not isinstance(other, Phoneme):
            return NotImplemented
        return self.symbol == other.symbol and self.language == other.language

    def __hash__(self) -> int:
        """Hash based on symbol and language."""
        return hash((self.symbol, self.language))


@dataclass
class Transcript:
    """Transcript entity.

    Represents text transcription with phoneme IDs for TTS.
    """

    id: str
    text: str
    phoneme_ids: list[int]
    language: str

    def __post_init__(self) -> None:
        """Validate transcript on creation."""
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")

        if not self.phoneme_ids:
            raise ValueError("Phoneme IDs cannot be empty")

    def normalized_text(self) -> str:
        """Return normalized text with cleaned whitespace."""
        # Remove excessive whitespace
        normalized = re.sub(r"\s+", " ", self.text)
        return normalized.strip()


@dataclass
class AudioSample:
    """Audio sample entity.

    Represents a single audio recording with its metadata and quality metrics.
    """

    id: str
    file_path: Path
    sample_rate: SampleRate
    duration: Duration
    format: AudioFormat
    quality: AudioQuality

    def is_valid(self) -> bool:
        """Check if audio sample meets quality standards."""
        is_valid, _ = self.quality.validate()
        return is_valid


@dataclass
class Voice:
    """Voice aggregate root.

    Represents a complete voice model with all its audio samples.
    This is the aggregate root that maintains consistency and business rules.
    """

    id: str
    name: str
    language: str
    sample_rate: SampleRate
    quality_level: str
    samples: list[AudioSample] = field(default_factory=list)

    def add_sample(self, sample: AudioSample) -> None:
        """Add an audio sample to the voice.

        Args:
            sample: The audio sample to add

        Raises:
            ValueError: If sample has different sample rate than voice
        """
        # Enforce consistency: all samples must have same sample rate
        if sample.sample_rate != self.sample_rate:
            raise ValueError(
                f"Sample rate mismatch: voice requires {self.sample_rate}, "
                f"sample has {sample.sample_rate}"
            )

        self.samples.append(sample)

    def total_duration_seconds(self) -> float:
        """Calculate total duration of all samples in seconds."""
        return sum(sample.duration.seconds for sample in self.samples)

    def valid_sample_count(self) -> int:
        """Count number of samples that meet quality standards."""
        return sum(1 for sample in self.samples if sample.is_valid())

    def invalid_sample_count(self) -> int:
        """Count number of samples that don't meet quality standards."""
        return len(self.samples) - self.valid_sample_count()


@dataclass
class PhonemeMap:
    """Phoneme map entity for Japanese phonetization.

    Central authority for managing hiragana-to-phoneme-ID mappings.
    Ensures deterministic and reproducible phoneme ID assignment.
    """

    max_phonemes: int = 200
    phonemes: list[PhonemeValue] = field(default_factory=list)
    _char_to_id: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _id_to_char: dict[int, str] = field(default_factory=dict, init=False, repr=False)

    def add_phoneme(self, character: str) -> None:
        """Add a phoneme to the map.

        Args:
            character: Hiragana character

        Raises:
            ValueError: If max phonemes limit exceeded
        """
        # Check if already exists (idempotent)
        if character in self._char_to_id:
            return

        # Check max phonemes limit
        if len(self.phonemes) >= self.max_phonemes:
            raise ValueError(
                f"Maximum number of phonemes ({self.max_phonemes}) exceeded"
            )

        # Assign next ID
        phoneme_id = len(self.phonemes)
        phoneme = PhonemeValue(character=character, id=phoneme_id)

        self.phonemes.append(phoneme)
        self._char_to_id[character] = phoneme_id
        self._id_to_char[phoneme_id] = character

    def get_phoneme_id(self, character: str) -> int:
        """Get phoneme ID for a character.

        Args:
            character: Hiragana character

        Returns:
            Phoneme ID

        Raises:
            KeyError: If character not in map
        """
        if character not in self._char_to_id:
            raise KeyError(f"Phoneme not found for character: {character}")

        return self._char_to_id[character]

    def get_phoneme_char(self, phoneme_id: int) -> str:
        """Get phoneme character for an ID.

        Args:
            phoneme_id: Phoneme ID

        Returns:
            Hiragana character

        Raises:
            KeyError: If ID not in map
        """
        if phoneme_id not in self._id_to_char:
            raise KeyError(f"Phoneme ID not found: {phoneme_id}")

        return self._id_to_char[phoneme_id]

    def has_phoneme(self, character: str) -> bool:
        """Check if phoneme exists in map.

        Args:
            character: Hiragana character

        Returns:
            True if phoneme exists
        """
        return character in self._char_to_id

    def phonemize(self, text: HiraganaText) -> PhonemeSequence:
        """Convert hiragana text to phoneme ID sequence.

        Args:
            text: Hiragana text

        Returns:
            PhonemeSequence

        Raises:
            KeyError: If text contains character not in map
        """
        phoneme_ids: list[int] = []

        for char in text.value:
            # Skip spaces (not phonemes)
            if char == " ":
                continue

            # Get phoneme ID
            if char not in self._char_to_id:
                raise KeyError(f"Phoneme not found for character: {char}")

            phoneme_ids.append(self._char_to_id[char])

        return PhonemeSequence(phoneme_ids)

    @classmethod
    def build_from_texts(cls, texts: list[HiraganaText]) -> "PhonemeMap":
        """Factory method to build phoneme map from texts.

        Args:
            texts: List of hiragana texts

        Returns:
            PhonemeMap with all unique phonemes
        """
        phoneme_map = cls()

        # Collect unique characters
        unique_chars: set[str] = set()
        for text in texts:
            for char in text.value:
                # Skip spaces
                if char != " ":
                    unique_chars.add(char)

        # Add phonemes in sorted order (deterministic)
        for char in sorted(unique_chars):
            phoneme_map.add_phoneme(char)

        return phoneme_map

    def to_dict(self) -> dict[str, dict[str, int]]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with phoneme mappings
        """
        return {
            "phonemes": {
                phoneme.character: phoneme.id for phoneme in self.phonemes
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PhonemeMap":
        """Create PhonemeMap from dictionary.

        Args:
            data: Dictionary with phoneme mappings

        Returns:
            PhonemeMap instance
        """
        phoneme_map = cls()

        # Sort by ID to ensure correct order
        phonemes_data = data["phonemes"]
        sorted_items = sorted(phonemes_data.items(), key=lambda x: x[1])

        for char, _phoneme_id in sorted_items:
            phoneme_map.add_phoneme(char)

        return phoneme_map

    def save_to_json(self, file_path: Path) -> None:
        """Save phoneme map to JSON file.

        Args:
            file_path: Path to JSON file
        """
        import json

        data = self.to_dict()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, file_path: Path) -> "PhonemeMap":
        """Load phoneme map from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            PhonemeMap instance
        """
        import json

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    def __len__(self) -> int:
        """Return number of phonemes in map."""
        return len(self.phonemes)
