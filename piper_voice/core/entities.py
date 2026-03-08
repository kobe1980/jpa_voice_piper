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
    SampleRate,
)


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
