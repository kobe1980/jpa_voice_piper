#!/usr/bin/env python3
"""CLI script for Piper preprocessing.

Usage:
    python scripts/preprocess_piper.py \\
        --input-metadata dataset/metadata_phonemes.csv \\
        --phoneme-map dataset/phoneme_map.json \\
        --audio-dir dataset/wav \\
        --output-dir training/ \\
        --sample-rate 22050

This script:
1. Validates all inputs exist
2. Transforms metadata CSV → dataset.jsonl
3. Calculates audio normalization statistics
4. Generates Piper config.json with custom phoneme mappings
5. Validates all outputs
"""

import argparse
import logging
import sys
from pathlib import Path

from piper_voice.application.preprocess_japanese_dataset import (
    PreprocessConfig,
    preprocess_japanese_dataset,
)


def setup_logging() -> None:
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Preprocess Japanese dataset for Piper TTS training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (22050 Hz)
  python scripts/preprocess_piper.py \\
      --input-metadata dataset/metadata_phonemes.csv \\
      --phoneme-map dataset/phoneme_map.json \\
      --audio-dir dataset/wav \\
      --output-dir training/ \\
      --sample-rate 22050

  # With 16000 Hz sample rate
  python scripts/preprocess_piper.py \\
      --input-metadata dataset/metadata_phonemes.csv \\
      --phoneme-map dataset/phoneme_map.json \\
      --audio-dir dataset/wav \\
      --output-dir training/ \\
      --sample-rate 16000 \\
      --verbose
        """,
    )

    parser.add_argument(
        "--input-metadata",
        type=Path,
        required=True,
        help="Input metadata_phonemes.csv (audio_file|phoneme_ids format)",
    )

    parser.add_argument(
        "--phoneme-map",
        type=Path,
        required=True,
        help="Phoneme map JSON file (hiragana → ID mappings)",
    )

    parser.add_argument(
        "--audio-dir",
        type=Path,
        required=True,
        help="Directory containing audio WAV files",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for preprocessing results",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        required=True,
        choices=[16000, 22050],
        help="Audio sample rate (16000 or 22050 Hz)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for preprocessing script.

    Returns:
        0 on success, 1 on error
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate inputs exist
    if not args.input_metadata.exists():
        logger.error(f"Input metadata not found: {args.input_metadata}")
        return 1

    if not args.phoneme_map.exists():
        logger.error(f"Phoneme map not found: {args.phoneme_map}")
        return 1

    if not args.audio_dir.exists():
        logger.error(f"Audio directory not found: {args.audio_dir}")
        return 1

    # Create config
    config = PreprocessConfig(
        input_metadata=args.input_metadata,
        phoneme_map_path=args.phoneme_map,
        audio_dir=args.audio_dir,
        output_dir=args.output_dir,
        sample_rate=args.sample_rate,
    )

    logger.info("Starting Piper preprocessing...")
    logger.info(f"Input metadata: {args.input_metadata}")
    logger.info(f"Phoneme map: {args.phoneme_map}")
    logger.info(f"Audio directory: {args.audio_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Sample rate: {args.sample_rate} Hz")

    # Run preprocessing
    try:
        logger.info("Phase 1: Validating inputs...")
        logger.info("Phase 2: Loading phoneme map...")
        logger.info("Phase 3: Transforming metadata CSV → JSONL...")
        logger.info("Phase 4: Calculating audio normalization statistics...")
        logger.info("Phase 5: Generating Piper config.json...")

        result = preprocess_japanese_dataset(config)

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return 1

    # Report results
    logger.info("✅ Preprocessing complete!")
    logger.info(f"Total samples: {result.total_samples}")

    if result.skipped_samples > 0:
        logger.warning(f"Skipped samples: {result.skipped_samples} (corrupted files)")
        logger.warning(f"Corrupted files: {', '.join(result.corrupted_files)}")

    logger.info(f"Unique phonemes: {result.phoneme_count}")
    logger.info("")
    logger.info("Output files:")
    logger.info(f"  - dataset.jsonl: {result.dataset_jsonl}")
    logger.info(f"  - config.json: {result.config_json}")
    logger.info(f"  - audio_norm_stats.json: {result.audio_stats_json}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Verify outputs are correct")

    if result.corrupted_files:
        corrupted_list = ", ".join(result.corrupted_files)
        logger.info(f"2. Fix or remove corrupted files: {corrupted_list}")
        logger.info("3. Run preprocessing again")
        logger.info("4. Run Piper training:")
    else:
        logger.info("2. Run Piper training:")

    logger.info(f"   python -m piper_train --dataset-dir {args.output_dir} ...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
