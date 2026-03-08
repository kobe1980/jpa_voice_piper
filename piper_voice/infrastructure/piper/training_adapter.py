"""Piper training adapter using subprocess."""

import logging
import subprocess
from pathlib import Path

from piper_voice.core.entities import TrainingRun
from piper_voice.core.value_objects import TrainingConfig

logger = logging.getLogger(__name__)


class PiperTrainingAdapter:
    """Adapter for Piper training using subprocess."""

    def start_training(
        self,
        dataset_dir: Path,
        output_dir: Path,
        config: TrainingConfig,
        resume_checkpoint: Path | None = None,
    ) -> subprocess.Popen:
        """Start Piper training in subprocess.

        Args:
            dataset_dir: Directory with dataset.jsonl and config.json
            output_dir: Output directory for logs and checkpoints
            config: Training configuration
            resume_checkpoint: Optional checkpoint to resume from

        Returns:
            Subprocess handle for training process
        """
        # Build piper_train command
        cmd = [
            "python",
            "-m",
            "piper_train",
            "--dataset-dir",
            str(dataset_dir),
            "--output-dir",
            str(output_dir),
            "--batch-size",
            str(config.batch_size),
            "--learning-rate",
            str(config.learning_rate),
            "--max-epochs",
            str(config.max_epochs),
            "--val-split",
            str(config.validation_split),
            "--checkpoint-epochs",
            str(config.checkpoint_epochs),
            "--gradient-clip-val",
            str(config.gradient_clip_val),
            "--accelerator",
            config.accelerator.value,
        ]

        # Add resume checkpoint if provided
        if resume_checkpoint:
            cmd.extend(["--resume-from-checkpoint", str(resume_checkpoint)])

        logger.info(f"Starting training with command: {' '.join(cmd)}")

        # Start training subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        return process

    def monitor_progress(
        self, process: subprocess.Popen, training_run: TrainingRun
    ) -> None:
        """Monitor training progress from subprocess output.

        Args:
            process: Training subprocess
            training_run: TrainingRun entity to update
        """
        if process.stdout is None:
            return

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            logger.info(line)

            # Parse epoch and loss from output
            if "Epoch" in line and "loss" in line:
                try:
                    # Example: "Epoch 10: train_loss=2.345 val_loss=2.567"
                    parts = line.split()
                    epoch = int(parts[1].rstrip(":"))
                    train_loss = float(parts[2].split("=")[1])
                    val_loss = float(parts[3].split("=")[1]) if len(parts) > 3 else None

                    training_run.update_metrics(epoch, train_loss, val_loss)
                except (IndexError, ValueError) as e:
                    logger.debug(f"Could not parse metrics from line: {line} ({e})")

        # Wait for process to complete
        return_code = process.wait()

        if return_code == 0:
            training_run.complete()
        else:
            training_run.fail()
