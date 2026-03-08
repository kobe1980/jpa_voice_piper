"""Domain value objects for Piper Voice dataset.

Value objects are immutable and defined by their values, not identity.
They enforce domain invariants and validation rules.
"""

from dataclasses import dataclass


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
