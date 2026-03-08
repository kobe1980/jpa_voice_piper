"""Domain ports (interfaces) for Piper Voice dataset.

Ports define the contracts that infrastructure adapters must implement.
This follows the Hexagonal Architecture pattern (Ports and Adapters).

The domain depends on these abstract interfaces, never on concrete implementations.
"""

from pathlib import Path
from typing import Protocol

from piper_voice.core.value_objects import AudioQuality, HiraganaText, PhonemeSequence


class AudioProcessorPort(Protocol):
    """Port for audio processing operations.

    Infrastructure adapters must implement this interface to provide
    audio loading, analysis, and normalization capabilities.
    """

    def load_audio(self, file_path: Path) -> tuple[list[float], int]:
        """Load audio file and return samples and sample rate.

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (audio_samples, sample_rate)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        ...

    def analyze_quality(self, file_path: Path) -> AudioQuality:
        """Analyze audio file and return quality metrics.

        Args:
            file_path: Path to audio file

        Returns:
            AudioQuality value object with all metrics

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        ...

    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_sample_rate: int,
    ) -> None:
        """Normalize audio file to target sample rate and format.

        Args:
            input_path: Source audio file
            output_path: Destination audio file
            target_sample_rate: Target sample rate (16000 or 22050)

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If target sample rate is invalid
        """
        ...


class PhoneticsCheckerPort(Protocol):
    """Port for phonetic validation operations.

    Infrastructure adapters must implement this interface to provide
    phonetic transcription and validation capabilities.
    """

    def check_text(self, text: str, language: str) -> tuple[bool, list[str]]:
        """Check if text can be phonetized correctly.

        Args:
            text: Text to check
            language: Language code (e.g., "fr", "en")

        Returns:
            Tuple of (is_valid, error_messages)
        """
        ...

    def text_to_phoneme_ids(self, text: str, language: str) -> list[int]:
        """Convert text to phoneme IDs.

        Args:
            text: Text to convert
            language: Language code (e.g., "fr", "en")

        Returns:
            List of phoneme IDs

        Raises:
            ValueError: If text cannot be phonetized
        """
        ...

    def get_phoneme_map(self, language: str) -> dict[str, int]:
        """Get phoneme symbol to ID mapping for language.

        Args:
            language: Language code (e.g., "fr", "en")

        Returns:
            Dictionary mapping phoneme symbols to IDs
        """
        ...


class FileSystemPort(Protocol):
    """Port for safe filesystem operations.

    Infrastructure adapters must implement this interface to provide
    controlled file access respecting security guardrails.
    """

    def is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories.

        Args:
            path: Path to check

        Returns:
            True if path is allowed by security policy
        """
        ...

    def list_audio_files(self, directory: Path) -> list[Path]:
        """List all audio files in directory.

        Args:
            directory: Directory to search

        Returns:
            List of audio file paths

        Raises:
            PermissionError: If directory is not allowed
            FileNotFoundError: If directory doesn't exist
        """
        ...

    def ensure_directory(self, path: Path) -> None:
        """Create directory if it doesn't exist.

        Args:
            path: Directory path to create

        Raises:
            PermissionError: If path is not allowed
        """
        ...


class MetadataRepositoryPort(Protocol):
    """Port for metadata persistence operations.

    Infrastructure adapters must implement this interface to provide
    metadata storage and retrieval in LJSPEECH format.
    """

    def save_metadata(
        self,
        samples: list[tuple[str, str]],
        output_path: Path,
    ) -> None:
        """Save metadata in LJSPEECH format.

        Args:
            samples: List of (audio_filename, transcription) tuples
            output_path: Path to metadata.csv file

        Raises:
            PermissionError: If path is not allowed
        """
        ...

    def load_metadata(self, input_path: Path) -> list[tuple[str, str]]:
        """Load metadata from LJSPEECH format file.

        Args:
            input_path: Path to metadata.csv file

        Returns:
            List of (audio_filename, transcription) tuples

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        ...


class PiperTrainingPort(Protocol):
    """Port for Piper training operations.

    Infrastructure adapters must implement this interface to provide
    Piper preprocessing and training capabilities.
    """

    def preprocess_dataset(
        self,
        dataset_dir: Path,
        output_dir: Path,
        language: str,
        sample_rate: int,
    ) -> None:
        """Run Piper preprocessing on dataset.

        Args:
            dataset_dir: Directory containing metadata.csv and audio
            output_dir: Output directory for preprocessed data
            language: Language code (e.g., "fr-fr")
            sample_rate: Audio sample rate (16000 or 22050)

        Raises:
            FileNotFoundError: If dataset_dir doesn't exist
            ValueError: If preprocessing fails
        """
        ...

    def train_voice(
        self,
        config_path: Path,
        checkpoint_path: Path | None,
        output_dir: Path,
    ) -> None:
        """Train voice model with Piper.

        Args:
            config_path: Path to training config
            checkpoint_path: Optional checkpoint to resume from
            output_dir: Output directory for checkpoints and logs

        Raises:
            FileNotFoundError: If config doesn't exist
            ValueError: If training fails
        """
        ...

    def export_onnx(
        self,
        checkpoint_path: Path,
        output_path: Path,
    ) -> None:
        """Export trained model to ONNX format.

        Args:
            checkpoint_path: Path to trained checkpoint
            output_path: Path to output ONNX file

        Raises:
            FileNotFoundError: If checkpoint doesn't exist
            ValueError: If export fails
        """
        ...


class KanjiConverterPort(Protocol):
    """Port for kanji-to-hiragana conversion.

    Infrastructure adapters (e.g., pykakasi) must implement this interface
    to provide Japanese text conversion capabilities.
    """

    def convert_to_hiragana(self, text: str) -> HiraganaText:
        """Convert Japanese text (kanji + kana) to pure hiragana.

        Args:
            text: Japanese text (may contain kanji, hiragana, katakana)

        Returns:
            HiraganaText value object (validated pure hiragana)

        Raises:
            ValueError: If conversion fails or produces invalid hiragana
        """
        ...


class PhonetizerPort(Protocol):
    """Port for text-to-phoneme conversion.

    Infrastructure adapters must implement this interface to provide
    phonemization capabilities for TTS training.
    """

    def phonemize(self, text: HiraganaText) -> PhonemeSequence:
        """Convert hiragana text to phoneme ID sequence.

        Args:
            text: Hiragana text to phonemize

        Returns:
            PhonemeSequence with phoneme IDs

        Raises:
            KeyError: If text contains character not in phoneme map
            ValueError: If phonemization fails
        """
        ...
