#!/usr/bin/env python3
"""CLI script for preparing JSUT dataset.

Downloads and prepares the JSUT (Japanese Speech corpus) dataset for Piper training.

Usage:
    # Download JSUT basic5000
    ./scripts/download_jsut.sh

    # Prepare dataset
    python scripts/prepare_jsut_dataset.py \\
        --jsut-dir dataset/jsut/basic5000 \\
        --output-dir dataset/prepared \\
        --sample-rate 22050
"""

import argparse
import logging
import sys
from pathlib import Path

from piper_voice.application.prepare_dataset import (
    DatasetConfig,
    prepare_dataset,
)
from piper_voice.core.value_objects import SampleRate
from piper_voice.infrastructure.audio.processor import LibrosaAudioProcessor
from piper_voice.infrastructure.filesystem.jsut_loader import JSUTLoader
from piper_voice.infrastructure.filesystem.metadata_writer import MetadataWriter
from piper_voice.infrastructure.filesystem.safe_fs import SafeFilesystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Prepare JSUT dataset for Piper training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--jsut-dir",
        type=Path,
        required=True,
        help="Path to JSUT dataset directory (e.g., dataset/jsut/basic5000)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for prepared dataset",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        choices=[16000, 22050],
        default=22050,
        help="Target sample rate (default: 22050 Hz)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output directory",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Validate JSUT directory
    if not args.jsut_dir.exists():
        logger.error(f"JSUT directory not found: {args.jsut_dir}")
        logger.info("")
        logger.info("To download JSUT dataset:")
        logger.info("  mkdir -p dataset/jsut")
        logger.info("  cd dataset/jsut")
        logger.info("  wget http://ss-takashi.sakura.ne.jp/corpus/jsut_ver1.1.zip")
        logger.info("  unzip jsut_ver1.1.zip")
        logger.info("  mv jsut_ver1.1/* .")
        logger.info("")
        return 1

    # Check if output directory exists
    if args.output_dir.exists() and not args.force:
        logger.error(f"Output directory already exists: {args.output_dir}")
        logger.info("Use --force to overwrite")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize components
    jsut_loader = JSUTLoader()
    audio_processor = LibrosaAudioProcessor()
    metadata_writer = MetadataWriter()
    filesystem = SafeFilesystem()

    # Create configuration
    sample_rate = SampleRate(args.sample_rate)
    config = DatasetConfig(
        input_dir=args.jsut_dir,
        output_dir=args.output_dir,
        sample_rate=sample_rate,
    )

    # Print configuration
    logger.info("=" * 80)
    logger.info("JSUT Dataset Preparation")
    logger.info("=" * 80)
    logger.info(f"JSUT directory: {args.jsut_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Target sample rate: {args.sample_rate} Hz")
    logger.info("=" * 80)

    try:
        # Prepare dataset
        logger.info("Starting dataset preparation...")
        result = prepare_dataset(
            config=config,
            dataset_loader=jsut_loader,
            audio_processor=audio_processor,
            metadata_writer=metadata_writer,
            filesystem=filesystem,
        )

        # Print results
        logger.info("=" * 80)
        logger.info("Preparation Results")
        logger.info("=" * 80)
        logger.info(f"Success: {result.success}")
        logger.info(f"Total samples: {result.total_samples}")
        logger.info(f"Valid samples: {result.valid_samples}")
        logger.info(f"Invalid samples: {result.invalid_samples}")
        logger.info(f"Total duration: {result.total_duration_seconds:.1f} seconds")
        logger.info(f"Output metadata: {result.metadata_path}")
        logger.info("=" * 80)

        if result.errors:
            logger.warning(f"Encountered {len(result.errors)} errors:")
            for error in result.errors[:10]:  # Show first 10 errors
                logger.warning(f"  - {error}")
            if len(result.errors) > 10:
                logger.warning(f"  ... and {len(result.errors) - 10} more")

        if result.success:
            logger.info("✅ Dataset preparation completed successfully!")
            logger.info("")
            logger.info("Next steps:")
            logger.info(f"  1. Phonemize corpus:")
            logger.info(f"     python scripts/phonemize_japanese.py \\")
            logger.info(f"       --input {result.metadata_path} \\")
            logger.info(f"       --output {args.output_dir}/metadata_phonemes.csv \\")
            logger.info(f"       --phoneme-map {args.output_dir}/phoneme_map.json")
            logger.info("")
            logger.info(f"  2. Preprocess for Piper:")
            logger.info(f"     python scripts/preprocess_piper.py \\")
            logger.info(f"       --input-metadata {args.output_dir}/metadata_phonemes.csv \\")
            logger.info(f"       --phoneme-map {args.output_dir}/phoneme_map.json \\")
            logger.info(f"       --audio-dir {args.output_dir}/wav \\")
            logger.info(f"       --output-dir training \\")
            logger.info(f"       --sample-rate {args.sample_rate}")
            logger.info("")
            logger.info(f"  3. Train voice model:")
            logger.info(f"     python scripts/train_voice.py \\")
            logger.info(f"       --dataset-dir training \\")
            logger.info(f"       --output-dir output \\")
            logger.info(f"       --checkpoint-dir checkpoints \\")
            logger.info(f"       --fast-experiment")
            return 0
        else:
            logger.error("❌ Dataset preparation failed!")
            return 1

    except Exception as e:
        logger.exception(f"Dataset preparation failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
