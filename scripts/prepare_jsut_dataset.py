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

from piper_voice.application.prepare_dataset import PrepareDatasetUseCase
from piper_voice.infrastructure.audio.processor import LibrosaAudioProcessor
from piper_voice.infrastructure.filesystem.safe_fs import SafeFileSystem

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

    # Determine project root (current working directory)
    project_root = Path.cwd()

    # Initialize components
    audio_processor = LibrosaAudioProcessor()
    filesystem = SafeFileSystem(project_root)

    # Create use case
    use_case = PrepareDatasetUseCase(filesystem, audio_processor)

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
        result = use_case.execute(
            jsut_root=args.jsut_dir,
            output_dir=args.output_dir,
            target_sample_rate=args.sample_rate,
            validate_quality=False,  # Skip quality validation for JSUT (already high quality)
            normalize_audio=True,     # Normalize to target sample rate
        )

        # Print results
        logger.info("=" * 80)
        logger.info("Preparation Results")
        logger.info("=" * 80)
        logger.info(f"Success: {result.success}")
        logger.info(f"Message: {result.message}")
        logger.info(f"Total samples: {result.total_samples}")
        logger.info(f"Failed samples: {result.failed_samples}")
        logger.info(f"Valid samples: {result.total_samples - result.failed_samples}")
        logger.info("=" * 80)

        if result.success:
            logger.info("✅ Dataset preparation completed successfully!")
            logger.info("")
            logger.info("Next steps:")
            logger.info(f"  1. Verify metadata.csv:")
            logger.info(f"     head -n 5 {args.output_dir}/metadata.csv")
            logger.info("")
            logger.info(f"  2. Check normalized audio files:")
            logger.info(f"     ls -lh {args.output_dir}/wav/ | head")
            logger.info("")
            logger.info(f"  3. Preprocess for Piper training:")
            logger.info(f"     python -m piper_train.preprocess \\")
            logger.info(f"       --language ja-jp \\")
            logger.info(f"       --input-dir {args.output_dir} \\")
            logger.info(f"       --output-dir ./training \\")
            logger.info(f"       --dataset-format ljspeech \\")
            logger.info(f"       --single-speaker \\")
            logger.info(f"       --sample-rate {args.sample_rate}")
            logger.info("")
            logger.info(f"  4. Train voice model:")
            logger.info(f"     python -m piper_train \\")
            logger.info(f"       --dataset-dir ./training \\")
            logger.info(f"       --accelerator 'gpu' \\")
            logger.info(f"       --devices 1 \\")
            logger.info(f"       --batch-size 32 \\")
            logger.info(f"       --max_epochs 10000")
            return 0
        else:
            logger.error("❌ Dataset preparation failed!")
            return 1

    except Exception as e:
        logger.exception(f"Dataset preparation failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
