"""Dataset preparation use case.

This module orchestrates the complete dataset preparation pipeline:
1. Load corpus (JSUT)
2. Validate audio quality (optional)
3. Normalize audio files (optional)
4. Generate metadata.csv (LJSPEECH format)
"""

from dataclasses import dataclass
from pathlib import Path

from piper_voice.infrastructure.audio.processor import LibrosaAudioProcessor
from piper_voice.infrastructure.filesystem.jsut_loader import JsutCorpusLoader
from piper_voice.infrastructure.filesystem.metadata_writer import (
    LJSpeechMetadataWriter,
)
from piper_voice.infrastructure.filesystem.safe_fs import SafeFileSystem


@dataclass
class PrepareDatasetResult:
    """Result of dataset preparation operation."""

    success: bool
    message: str
    total_samples: int = 0
    failed_samples: int = 0


class PrepareDatasetUseCase:
    """Use case for preparing dataset for Piper training.

    Orchestrates:
    - Corpus loading
    - Audio quality validation
    - Audio normalization
    - Metadata generation
    """

    def __init__(
        self,
        filesystem: SafeFileSystem,
        audio_processor: LibrosaAudioProcessor,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            filesystem: Filesystem operations adapter
            audio_processor: Audio processing adapter
        """
        self.filesystem = filesystem
        self.audio_processor = audio_processor

    def execute(
        self,
        jsut_root: Path,
        output_dir: Path,
        target_sample_rate: int = 22050,
        validate_quality: bool = False,
        normalize_audio: bool = False,
    ) -> PrepareDatasetResult:
        """Prepare dataset from JSUT corpus.

        Args:
            jsut_root: Path to JSUT corpus root directory
            output_dir: Output directory for prepared dataset
            target_sample_rate: Target sample rate for normalized audio
            validate_quality: Whether to validate audio quality
            normalize_audio: Whether to normalize audio files

        Returns:
            PrepareDatasetResult with success status and statistics
        """
        try:
            # Step 1: Validate output directory security
            if not self.filesystem.is_path_allowed(output_dir):
                return PrepareDatasetResult(
                    success=False,
                    message=(
                        f"Output directory {output_dir} is not allowed "
                        "by security policy"
                    ),
                )

            # Step 2: Load corpus
            loader = JsutCorpusLoader(jsut_root)
            try:
                pairs = loader.load_corpus()
            except (FileNotFoundError, ValueError) as e:
                return PrepareDatasetResult(
                    success=False,
                    message=f"Failed to load corpus: {e}",
                )

            if not pairs:
                return PrepareDatasetResult(
                    success=False,
                    message="No audio-transcript pairs found in corpus",
                )

            # Step 3: Validate audio quality (optional)
            valid_pairs: list[tuple[Path, str]] = []
            failed_count = 0

            for audio_path, transcript in pairs:
                if validate_quality:
                    try:
                        quality = self.audio_processor.analyze_quality(audio_path)
                        is_valid, errors = quality.validate()

                        if not is_valid:
                            failed_count += 1
                            continue  # Skip this file

                    except Exception:
                        failed_count += 1
                        continue  # Skip files that can't be analyzed

                valid_pairs.append((audio_path, transcript))

            if not valid_pairs:
                return PrepareDatasetResult(
                    success=False,
                    message="No valid audio files found after quality validation",
                    total_samples=len(pairs),
                    failed_samples=failed_count,
                )

            # Step 4: Normalize audio files (optional)
            if normalize_audio:
                # Create wav output directory
                wav_dir = output_dir / "wav"
                self.filesystem.ensure_directory(wav_dir)

                normalized_pairs: list[tuple[Path, str]] = []

                for audio_path, transcript in valid_pairs:
                    try:
                        # Normalize audio
                        output_audio = wav_dir / audio_path.name
                        self.audio_processor.normalize_audio(
                            audio_path, output_audio, target_sample_rate
                        )

                        # Update pair to point to normalized file
                        normalized_pairs.append((output_audio, transcript))

                    except Exception:
                        failed_count += 1
                        continue  # Skip files that fail normalization

                valid_pairs = normalized_pairs

            # Step 5: Generate metadata.csv
            metadata_writer = LJSpeechMetadataWriter(output_dir)
            try:
                metadata_writer.write_metadata(valid_pairs)
            except Exception as e:
                return PrepareDatasetResult(
                    success=False,
                    message=f"Failed to write metadata: {e}",
                    total_samples=len(pairs),
                    failed_samples=failed_count,
                )

            # Success
            return PrepareDatasetResult(
                success=True,
                message=f"Dataset prepared successfully: {len(valid_pairs)} samples",
                total_samples=len(pairs),
                failed_samples=failed_count,
            )

        except Exception as e:
            return PrepareDatasetResult(
                success=False,
                message=f"Unexpected error: {e}",
            )
