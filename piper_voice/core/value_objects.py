"""Domain value objects for Piper Voice dataset.

Value objects are immutable and defined by their values, not identity.
They enforce domain invariants and validation rules.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class SampleRate:
    """Audio sample rate value object.

    Only 16000 Hz and 22050 Hz are supported per Piper requirements.
    """

    value: int

    def __post_init__(self) -> None:
        """Validate sample rate on creation."""
        if self.value not in (16000, 22050):
            raise ValueError(f"Sample rate must be 16000 or 22050 Hz, got {self.value}")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value} Hz"


@dataclass(frozen=True)
class Duration:
    """Audio duration value object.

    Duration must be between 1 and 15 seconds per Piper requirements.
    """

    seconds: float

    def __post_init__(self) -> None:
        """Validate duration on creation."""
        if not (1.0 <= self.seconds <= 15.0):
            raise ValueError(
                f"Duration must be between 1 and 15 seconds, got {self.seconds}"
            )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.seconds}s"


@dataclass(frozen=True)
class AudioFormat:
    """Audio format value object.

    Only WAV PCM_16 format is supported per Piper requirements.
    """

    type: str
    encoding: str

    def __post_init__(self) -> None:
        """Validate audio format on creation."""
        if self.type != "WAV":
            raise ValueError(f"Only WAV format is supported, got {self.type}")

        if self.encoding != "PCM_16":
            raise ValueError(f"Only PCM_16 encoding is supported, got {self.encoding}")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.type} {self.encoding}"


@dataclass(frozen=True)
class AudioQuality:
    """Audio quality metrics value object.

    Defines quality standards:
    - SNR: Signal-to-Noise Ratio must be >= 30 dB
    - Max amplitude: Peak amplitude must be < 0.95 (no clipping)
    - Silence: Start/end silence must be < 0.3 seconds
    """

    snr_db: float
    max_amplitude: float
    has_clipping: bool
    silence_at_start_sec: float
    silence_at_end_sec: float

    def validate(self) -> tuple[bool, list[str]]:
        """Validate audio quality against standards.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        # Check SNR
        if self.snr_db < 30.0:
            errors.append(f"SNR {self.snr_db:.1f} dB is below minimum 30 dB")

        # Check clipping
        if self.has_clipping or self.max_amplitude >= 0.95:
            errors.append(
                f"Clipping detected (max amplitude: {self.max_amplitude:.3f})"
            )

        # Check silence at start
        if self.silence_at_start_sec > 0.3:
            errors.append(
                f"Excessive silence at start: "
                f"{self.silence_at_start_sec:.2f}s (max 0.3s)"
            )

        # Check silence at end
        if self.silence_at_end_sec > 0.3:
            errors.append(
                f"Excessive silence at end: {self.silence_at_end_sec:.2f}s (max 0.3s)"
            )

        return (len(errors) == 0, errors)


@dataclass(frozen=True)
class Phoneme:
    """Phoneme value object for Japanese phonetization.

    Represents a single phoneme with its hiragana character and unique ID.
    """

    character: str
    id: int

    def __post_init__(self) -> None:
        """Validate phoneme on creation."""
        if not self.character:
            raise ValueError("Phoneme character cannot be empty")

        if len(self.character) != 1:
            raise ValueError("Phoneme character must be exactly 1 character")

        if self.id < 0:
            raise ValueError("Phoneme ID must be non-negative")


@dataclass(frozen=True)
class HiraganaText:
    """Hiragana text value object.

    Validates that text contains only hiragana characters (and allowed punctuation).
    Used after kanji-to-hiragana conversion.
    """

    value: str

    # Allowed characters for security
    SUSPICIOUS_CHARS = {"<", ">", ";", "&", "|", "`", "$", "\\"}
    MAX_LENGTH = 500

    def __post_init__(self) -> None:
        """Validate hiragana text on creation."""
        # Check not empty
        if not self.value or not self.value.strip():
            raise ValueError("Hiragana text cannot be empty")

        # Check length
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Hiragana text exceeds maximum length of {self.MAX_LENGTH} characters"
            )

        # Check for suspicious characters (security)
        for char in self.SUSPICIOUS_CHARS:
            if char in self.value:
                raise ValueError(
                    f"Hiragana text contains suspicious characters: {char}"
                )

        # Check for non-hiragana characters
        for char in self.value:
            # Allow hiragana (U+3040-U+309F)
            # Allow spaces, Japanese punctuation (、。「」・), and common marks
            if char in (" ", "、", "。", "「", "」", "・", "！", "？", "ー"):
                continue

            # Check if hiragana
            code = ord(char)
            if not (0x3040 <= code <= 0x309F):
                raise ValueError(
                    f"Hiragana text contains non-hiragana characters: {char}"
                )


@dataclass(frozen=True)
class PhonemeSequence:
    """Phoneme sequence value object.

    Represents a sequence of phoneme IDs for a transcript.
    """

    ids: list[int]

    def __post_init__(self) -> None:
        """Validate phoneme sequence on creation."""
        if not self.ids:
            raise ValueError("Phoneme sequence cannot be empty")

        # Check all IDs are non-negative
        for phoneme_id in self.ids:
            if phoneme_id < 0:
                raise ValueError(
                    f"All phoneme IDs must be non-negative, found {phoneme_id}"
                )

    def to_string(self) -> str:
        """Convert to space-separated string of phoneme IDs.

        Returns:
            Space-separated phoneme IDs (e.g., "0 1 2 3")
        """
        return " ".join(str(phoneme_id) for phoneme_id in self.ids)

    @classmethod
    def from_string(cls, phoneme_str: str) -> "PhonemeSequence":
        """Create PhonemeSequence from space-separated string.

        Args:
            phoneme_str: Space-separated phoneme IDs

        Returns:
            PhonemeSequence instance

        Raises:
            ValueError: If string is invalid
        """
        if not phoneme_str or not phoneme_str.strip():
            raise ValueError("Phoneme string cannot be empty")

        try:
            ids = [int(x) for x in phoneme_str.split()]
            return cls(ids)
        except ValueError as e:
            raise ValueError(f"Invalid phoneme ID in string: {phoneme_str}") from e

    def __len__(self) -> int:
        """Return number of phonemes in sequence."""
        return len(self.ids)


# Training value objects


class HardwareAccelerator(Enum):
    """Hardware accelerator types for training."""

    GPU = "gpu"  # CUDA GPU
    MPS = "mps"  # Apple Silicon GPU
    CPU = "cpu"  # CPU only


@dataclass(frozen=True)
class TrainingConfig:
    """Training configuration value object.

    Immutable configuration for Piper voice training with validated hyperparameters.
    """

    batch_size: int = 32
    learning_rate: float = 1e-4
    max_epochs: int = 1000
    validation_split: float = 0.1
    checkpoint_epochs: int = 50
    gradient_clip_val: float = 1.0
    accelerator: HardwareAccelerator = HardwareAccelerator.GPU

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if not 1 <= self.batch_size <= 128:
            raise ValueError("Batch size must be between 1 and 128")

        if not 1e-6 <= self.learning_rate <= 1e-2:
            raise ValueError("Learning rate must be between 1e-6 and 1e-2")

        if not 1 <= self.max_epochs <= 10000:
            raise ValueError("Max epochs must be between 1 and 10000")

        if not 0.05 <= self.validation_split <= 0.3:
            raise ValueError("Validation split must be between 0.05 and 0.3")

        if not 1 <= self.checkpoint_epochs <= 100:
            raise ValueError("Checkpoint epochs must be between 1 and 100")

        if not 0.1 <= self.gradient_clip_val <= 5.0:
            raise ValueError("Gradient clip val must be between 0.1 and 5.0")

    @classmethod
    def for_gpu(cls) -> "TrainingConfig":
        """Create config optimized for GPU training."""
        return cls(accelerator=HardwareAccelerator.GPU, batch_size=32)

    @classmethod
    def for_mps(cls) -> "TrainingConfig":
        """Create config optimized for Apple Silicon (MPS) training.

        Uses smaller batch size (8) to prevent OOM errors and improve stability
        with MPS backend.
        """
        return cls(accelerator=HardwareAccelerator.MPS, batch_size=8)

    @classmethod
    def for_cpu(cls) -> "TrainingConfig":
        """Create config optimized for CPU training."""
        return cls(accelerator=HardwareAccelerator.CPU, batch_size=8)

    @classmethod
    def for_fast_experiment(
        cls, accelerator: HardwareAccelerator = HardwareAccelerator.GPU
    ) -> "TrainingConfig":
        """Create config for fast experimentation (100 epochs).

        Args:
            accelerator: Hardware accelerator type (auto-determines optimal batch size)
        """
        # Use smaller batch size for MPS to avoid OOM
        batch_size = 8 if accelerator == HardwareAccelerator.MPS else 32
        return cls(
            max_epochs=100,
            checkpoint_epochs=10,
            batch_size=batch_size,
            accelerator=accelerator
        )

    @classmethod
    def for_high_quality(
        cls, accelerator: HardwareAccelerator = HardwareAccelerator.GPU
    ) -> "TrainingConfig":
        """Create config for high quality training (5000 epochs).

        Args:
            accelerator: Hardware accelerator type (auto-determines optimal batch size)
        """
        # Use smaller batch size for MPS to avoid OOM
        batch_size = 8 if accelerator == HardwareAccelerator.MPS else 32
        return cls(
            max_epochs=5000,
            learning_rate=5e-5,
            checkpoint_epochs=100,
            batch_size=batch_size,
            accelerator=accelerator
        )
