#!/usr/bin/env python3
"""CLI script for training Japanese voice with Piper.

Usage:
    python scripts/train_voice.py \\
        --dataset-dir ./training \\
        --output-dir ./output \\
        --checkpoint-dir ./checkpoints

Optional arguments:
    --batch-size 32
    --learning-rate 1e-4
    --max-epochs 1000
    --accelerator gpu|mps|cpu
    --no-base-checkpoint  # Train from scratch
    --fast-experiment     # Use fast experiment config (100 epochs)
    --high-quality        # Use high quality config (5000 epochs)
"""

import argparse
import logging
import sys
from pathlib import Path

from piper_voice.application.train_japanese_voice import (
    TrainingJobConfig,
    train_japanese_voice,
)
from piper_voice.core.value_objects import HardwareAccelerator, TrainingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train Japanese voice model with Piper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        required=True,
        help="Directory containing preprocessed dataset (dataset.jsonl, config.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for training logs and final model",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        required=True,
        help="Directory containing checkpoints (will create if doesn't exist)",
    )

    # Training configuration
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for training (default: auto-detect based on hardware)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help="Learning rate (default: 1e-4)",
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=None,
        help="Maximum number of epochs (default: 1000)",
    )
    parser.add_argument(
        "--validation-split",
        type=float,
        default=None,
        help="Validation split ratio (default: 0.1)",
    )
    parser.add_argument(
        "--checkpoint-epochs",
        type=int,
        default=None,
        help="Save checkpoint every N epochs (default: 50)",
    )
    parser.add_argument(
        "--gradient-clip-val",
        type=float,
        default=None,
        help="Gradient clipping value (default: 1.0)",
    )
    parser.add_argument(
        "--accelerator",
        type=str,
        choices=["gpu", "mps", "cpu"],
        default=None,
        help="Hardware accelerator (default: auto-detect)",
    )

    # Checkpoint options
    parser.add_argument(
        "--no-base-checkpoint",
        action="store_true",
        help="Train from scratch (don't use base checkpoint)",
    )

    # Preset configurations
    parser.add_argument(
        "--fast-experiment",
        action="store_true",
        help="Use fast experiment config (100 epochs, checkpoint every 10)",
    )
    parser.add_argument(
        "--high-quality",
        action="store_true",
        help="Use high quality config (5000 epochs, lower learning rate)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Validate mutually exclusive presets
    if args.fast_experiment and args.high_quality:
        logger.error("Cannot use both --fast-experiment and --high-quality")
        return 1

    # Build training configuration
    training_config: TrainingConfig | None = None

    if args.fast_experiment:
        logger.info("Using fast experiment configuration")
        training_config = TrainingConfig.for_fast_experiment()
    elif args.high_quality:
        logger.info("Using high quality configuration")
        training_config = TrainingConfig.for_high_quality()
    elif any(
        [
            args.batch_size,
            args.learning_rate,
            args.max_epochs,
            args.validation_split,
            args.checkpoint_epochs,
            args.gradient_clip_val,
            args.accelerator,
        ]
    ):
        # Build custom configuration
        logger.info("Using custom training configuration")

        # Parse accelerator
        accelerator = HardwareAccelerator.GPU
        if args.accelerator == "mps":
            accelerator = HardwareAccelerator.MPS
        elif args.accelerator == "cpu":
            accelerator = HardwareAccelerator.CPU

        training_config = TrainingConfig(
            batch_size=args.batch_size or 32,
            learning_rate=args.learning_rate or 1e-4,
            max_epochs=args.max_epochs or 1000,
            validation_split=args.validation_split or 0.1,
            checkpoint_epochs=args.checkpoint_epochs or 50,
            gradient_clip_val=args.gradient_clip_val or 1.0,
            accelerator=accelerator,
        )
    else:
        logger.info("Using auto-detected hardware configuration")
        # Will auto-detect in use case

    # Create job configuration
    job_config = TrainingJobConfig(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        checkpoint_dir=args.checkpoint_dir,
        training_config=training_config,
        use_base_checkpoint=not args.no_base_checkpoint,
    )

    # Print configuration summary
    logger.info("=" * 80)
    logger.info("Training Configuration Summary")
    logger.info("=" * 80)
    logger.info(f"Dataset directory: {job_config.dataset_dir}")
    logger.info(f"Output directory: {job_config.output_dir}")
    logger.info(f"Checkpoint directory: {job_config.checkpoint_dir}")
    logger.info(f"Use base checkpoint: {job_config.use_base_checkpoint}")
    if training_config:
        logger.info(f"Batch size: {training_config.batch_size}")
        logger.info(f"Learning rate: {training_config.learning_rate}")
        logger.info(f"Max epochs: {training_config.max_epochs}")
        logger.info(f"Validation split: {training_config.validation_split}")
        logger.info(f"Checkpoint epochs: {training_config.checkpoint_epochs}")
        logger.info(f"Gradient clip val: {training_config.gradient_clip_val}")
        logger.info(f"Accelerator: {training_config.accelerator.value}")
    logger.info("=" * 80)

    # Execute training
    try:
        logger.info("Starting training pipeline...")
        result = train_japanese_voice(job_config)

        # Print results
        logger.info("=" * 80)
        logger.info("Training Results")
        logger.info("=" * 80)
        logger.info(f"Success: {result.success}")
        logger.info(f"Final state: {result.training_run.state.value}")
        logger.info(f"Final epoch: {result.final_epoch}")
        if result.final_train_loss is not None:
            logger.info(f"Final train loss: {result.final_train_loss:.4f}")
        if result.final_validation_loss is not None:
            logger.info(f"Final validation loss: {result.final_validation_loss:.4f}")
        if result.error_message:
            logger.error(f"Error: {result.error_message}")
        logger.info("=" * 80)

        if result.success:
            logger.info("✅ Training completed successfully!")
            logger.info(f"Output directory: {job_config.output_dir}")
            logger.info(f"Checkpoints saved to: {job_config.checkpoint_dir}")
            return 0
        else:
            logger.error("❌ Training failed!")
            return 1

    except Exception as e:
        logger.exception(f"Training pipeline failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
