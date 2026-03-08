#!/usr/bin/env python3
"""CLI script for phonemizing Japanese corpus.

Usage:
    python scripts/phonemize_japanese.py \\
        --input dataset/metadata.csv \\
        --output dataset/metadata_phonemes.csv \\
        --phoneme-map dataset/phoneme_map.json

This script:
1. Loads Japanese text from metadata.csv (audio_file|japanese_text)
2. Converts kanji → hiragana using pykakasi
3. Builds phoneme map from unique hiragana characters
4. Converts hiragana → phoneme IDs
5. Saves metadata_phonemes.csv (audio_file|phoneme_ids) + phoneme_map.json
"""

import argparse
import logging
import sys
from pathlib import Path

from piper_voice.application.phonemize_japanese_corpus import (
    PhonemeCorpusConfig,
    phonemize_japanese_corpus,
)
from piper_voice.infrastructure.phonetics.pykakasi_adapter import PykakasiAdapter


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
        description="Phonemize Japanese corpus for Piper TTS training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/phonemize_japanese.py \\
      --input dataset/metadata.csv \\
      --output dataset/metadata_phonemes.csv \\
      --phoneme-map dataset/phoneme_map.json

  # With verbose logging
  python scripts/phonemize_japanese.py \\
      --input dataset/metadata.csv \\
      --output dataset/metadata_phonemes.csv \\
      --phoneme-map dataset/phoneme_map.json \\
      --verbose
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input metadata.csv (audio_file|japanese_text format)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output metadata_phonemes.csv (audio_file|phoneme_ids format)",
    )

    parser.add_argument(
        "--phoneme-map",
        type=Path,
        required=True,
        help="Output phoneme_map.json (character → ID mappings)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for phonemization script.

    Returns:
        0 on success, 1 on error
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input exists
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    # Create output directories if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.phoneme_map.parent.mkdir(parents=True, exist_ok=True)

    # Create config
    config = PhonemeCorpusConfig(
        input_metadata=args.input,
        output_metadata=args.output,
        phoneme_map_output=args.phoneme_map,
    )

    logger.info(f"Loading corpus from {args.input}")
    logger.info(f"Output will be written to {args.output}")
    logger.info(f"Phoneme map will be saved to {args.phoneme_map}")

    # Create kanji converter
    logger.info("Initializing pykakasi for kanji conversion...")
    kanji_converter = PykakasiAdapter()

    # Run phonemization
    logger.info("Starting phonemization (2-pass process)...")
    logger.info("Pass 1: Converting kanji → hiragana...")

    try:
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )
    except Exception as e:
        logger.error(f"Phonemization failed: {e}")
        return 1

    # Report results
    logger.info("Phonemization complete!")
    logger.info(f"Total samples: {result.total_samples}")
    logger.info(f"Successful: {result.successful}")
    logger.info(f"Failed: {result.failed}")
    logger.info(f"Unique phonemes: {result.phoneme_count}")

    if result.errors:
        logger.warning(f"Encountered {len(result.errors)} errors:")
        for error in result.errors[:10]:  # Show first 10 errors
            logger.warning(f"  {error}")
        if len(result.errors) > 10:
            logger.warning(f"  ... and {len(result.errors) - 10} more")

    if result.failed > 0:
        logger.warning(
            f"{result.failed}/{result.total_samples} samples failed phonemization"
        )
        return 1

    logger.info(f"✅ All {result.successful} samples phonemized successfully")
    logger.info(f"Output saved to {args.output}")
    logger.info(f"Phoneme map saved to {args.phoneme_map}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
