"""Train Japanese voice use case.

Orchestrates complete training pipeline from preprocessed dataset to trained model.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from piper_voice.core.entities import TrainingRun, TrainingState
from piper_voice.core.value_objects import HardwareAccelerator, TrainingConfig
from piper_voice.infrastructure.piper.checkpoint_manager import CheckpointManager
from piper_voice.infrastructure.piper.hardware_detector import HardwareDetector
from piper_voice.infrastructure.piper.training_adapter import PiperTrainingAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrainingJobConfig:
    """Configuration for training job."""

    dataset_dir: Path
    output_dir: Path
    checkpoint_dir: Path
    training_config: TrainingConfig | None = None
    use_base_checkpoint: bool = True


@dataclass
class TrainingResult:
    """Result of training job."""

    success: bool
    training_run: TrainingRun
    final_epoch: int
    final_train_loss: float | None
    final_validation_loss: float | None
    error_message: str | None = None


def train_japanese_voice(
    config: TrainingJobConfig,
) -> TrainingResult:
    """Train Japanese voice model with Piper.

    Args:
        config: Training job configuration

    Returns:
        TrainingResult with training outcome
    """
    # Phase 1: Validate inputs
    logger.info("Phase 1: Validating inputs")
    if not config.dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {config.dataset_dir}")

    dataset_jsonl = config.dataset_dir / "dataset.jsonl"
    config_json = config.dataset_dir / "config.json"

    if not dataset_jsonl.exists():
        raise FileNotFoundError(f"Dataset JSONL not found: {dataset_jsonl}")

    if not config_json.exists():
        raise FileNotFoundError(f"Config JSON not found: {config_json}")

    # Create output directories
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Phase 2: Detect hardware and configure training
    logger.info("Phase 2: Detecting hardware and configuring training")
    hardware_detector = HardwareDetector()
    detected_accelerator = hardware_detector.detect()

    # Use provided config or create default based on hardware
    if config.training_config is not None:
        training_config = config.training_config
    else:
        if detected_accelerator == HardwareAccelerator.GPU:
            training_config = TrainingConfig.for_gpu()
        elif detected_accelerator == HardwareAccelerator.MPS:
            training_config = TrainingConfig.for_mps()
        else:
            training_config = TrainingConfig.for_cpu()

    logger.info(f"Training configuration: {training_config}")

    # Phase 3: Find checkpoint to resume from
    logger.info("Phase 3: Looking for checkpoints")
    checkpoint_manager = CheckpointManager(config.checkpoint_dir)

    resume_checkpoint: Path | None = None

    # First, try to find latest checkpoint (resume interrupted training)
    latest_checkpoint = checkpoint_manager.find_latest_checkpoint()
    if latest_checkpoint and checkpoint_manager.validate_checkpoint(latest_checkpoint):
        logger.info(f"Found latest checkpoint: {latest_checkpoint}")
        resume_checkpoint = latest_checkpoint
    elif config.use_base_checkpoint:
        # Otherwise, try base checkpoint (transfer learning)
        base_checkpoint = checkpoint_manager.find_base_checkpoint()
        if base_checkpoint and checkpoint_manager.validate_checkpoint(base_checkpoint):
            logger.info(
                f"Using base checkpoint for transfer learning: {base_checkpoint}"
            )
            resume_checkpoint = base_checkpoint
        else:
            logger.info("No base checkpoint found, training from scratch")
    else:
        logger.info("Training from scratch (no checkpoint requested)")

    # Phase 4: Create training run entity
    logger.info("Phase 4: Initializing training run")
    training_run = TrainingRun(id=f"train_{config.dataset_dir.name}")
    training_run.start()

    # Phase 5: Start training subprocess
    logger.info("Phase 5: Starting Piper training subprocess")
    training_adapter = PiperTrainingAdapter()

    try:
        process = training_adapter.start_training(
            dataset_dir=config.dataset_dir,
            output_dir=config.output_dir,
            config=training_config,
            resume_checkpoint=resume_checkpoint,
        )

        # Phase 6: Monitor training progress
        logger.info("Phase 6: Monitoring training progress")
        training_adapter.monitor_progress(process, training_run)

        # Create result
        return TrainingResult(
            success=(training_run.state == TrainingState.COMPLETED),
            training_run=training_run,
            final_epoch=training_run.current_epoch,
            final_train_loss=training_run.train_loss,
            final_validation_loss=training_run.validation_loss,
            error_message=(
                None
                if training_run.state == TrainingState.COMPLETED
                else "Training failed"
            ),
        )

    except Exception as e:
        logger.error(f"Training failed with exception: {e}")
        training_run.fail()
        return TrainingResult(
            success=False,
            training_run=training_run,
            final_epoch=training_run.current_epoch,
            final_train_loss=training_run.train_loss,
            final_validation_loss=training_run.validation_loss,
            error_message=str(e),
        )
