"""Application use case for preprocessing Japanese dataset for Piper training.

This use case orchestrates the complete preprocessing pipeline:
1. Validate inputs
2. Load phoneme map
3. Transform metadata CSV → JSONL
4. Calculate audio normalization statistics
5. Generate Piper config.json
6. Validate outputs
"""

from dataclasses import dataclass
from pathlib import Path

from piper_voice.core.entities import PhonemeMap
from piper_voice.infrastructure.piper.audio_stats import AudioStatsCalculator
from piper_voice.infrastructure.piper.config_generator import PiperConfigGenerator
from piper_voice.infrastructure.piper.preprocessor_adapter import (
    PiperPreprocessorAdapter,
)


@dataclass(frozen=True)
class PreprocessConfig:
    """Configuration for dataset preprocessing.

    Attributes:
        input_metadata: Path to metadata_phonemes.csv (audio_file|phoneme_ids)
        phoneme_map_path: Path to phoneme_map.json
        audio_dir: Directory containing audio WAV files
        output_dir: Output directory for preprocessing results
        sample_rate: Audio sample rate (16000 or 22050)
    """

    input_metadata: Path
    phoneme_map_path: Path
    audio_dir: Path
    output_dir: Path
    sample_rate: int


@dataclass
class PreprocessResult:
    """Result of dataset preprocessing.

    Attributes:
        success: Whether preprocessing succeeded
        total_samples: Total number of samples processed
        phoneme_count: Number of unique phonemes in map
        dataset_jsonl: Path to generated dataset.jsonl
        config_json: Path to generated config.json
        audio_stats_json: Path to generated audio_norm_stats.json
    """

    success: bool
    total_samples: int
    phoneme_count: int
    dataset_jsonl: Path
    config_json: Path
    audio_stats_json: Path


def preprocess_japanese_dataset(config: PreprocessConfig) -> PreprocessResult:
    """Preprocess Japanese dataset for Piper training.

    Complete preprocessing pipeline:
    1. Validate all inputs exist
    2. Load phoneme map from JSON
    3. Transform metadata CSV → dataset.jsonl
    4. Calculate audio normalization statistics
    5. Generate Piper config.json with custom phonemes
    6. Return paths to all outputs

    Args:
        config: Preprocessing configuration

    Returns:
        PreprocessResult with statistics and output paths

    Raises:
        FileNotFoundError: If required inputs don't exist
        ValueError: If preprocessing fails
    """
    # Phase 1: Validate inputs
    if not config.input_metadata.exists():
        raise FileNotFoundError(f"Input metadata not found: {config.input_metadata}")

    if not config.phoneme_map_path.exists():
        raise FileNotFoundError(f"Phoneme map not found: {config.phoneme_map_path}")

    if not config.audio_dir.exists():
        raise FileNotFoundError(f"Audio directory not found: {config.audio_dir}")

    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    dataset_jsonl = config.output_dir / "dataset.jsonl"
    config_json = config.output_dir / "config.json"
    audio_stats_json = config.output_dir / "audio_norm_stats.json"

    # Phase 2: Load phoneme map
    phoneme_map = PhonemeMap.load_from_json(config.phoneme_map_path)

    # Phase 3: Transform metadata CSV → JSONL
    preprocessor = PiperPreprocessorAdapter()
    preprocessor.transform_to_jsonl(
        input_metadata=config.input_metadata,
        output_jsonl=dataset_jsonl,
        audio_dir=config.audio_dir,
    )

    # Count samples
    jsonl_lines = dataset_jsonl.read_text(encoding="utf-8").strip().split("\n")
    total_samples = len(jsonl_lines)

    # Phase 4: Calculate audio normalization statistics
    audio_files = list(config.audio_dir.glob("*.wav"))
    stats_calculator = AudioStatsCalculator()
    audio_stats = stats_calculator.calculate_stats(
        audio_files, expected_sample_rate=config.sample_rate
    )
    stats_calculator.save_stats(audio_stats, audio_stats_json)

    # Phase 5: Generate Piper config.json
    config_generator = PiperConfigGenerator()
    config_generator.generate_config(
        phoneme_map=phoneme_map,
        output_path=config_json,
        sample_rate=config.sample_rate,
        language="ja-jp",
    )

    # Phase 6: Return result
    return PreprocessResult(
        success=True,
        total_samples=total_samples,
        phoneme_count=len(phoneme_map.phonemes),
        dataset_jsonl=dataset_jsonl,
        config_json=config_json,
        audio_stats_json=audio_stats_json,
    )
