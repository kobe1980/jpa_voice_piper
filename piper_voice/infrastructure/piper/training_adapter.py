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
        # Build piper.train command
        # Note: piper.train expects a CSV file with phonemes and a phoneme_type
        # We use the metadata_phonemes.csv from dataset preparation
        csv_path = dataset_dir.parent / "dataset" / "prepared" / "metadata_phonemes.csv"
        audio_dir = dataset_dir.parent / "dataset" / "prepared" / "wav"
        cache_dir = dataset_dir
        config_path = dataset_dir / "config.json"

        cmd = [
            "python",
            "-m",
            "piper.train",
            "fit",
            "--data.voice_name",
            "ja_JP-jsut-medium",
            "--data.csv_path",
            str(csv_path),
            "--data.audio_dir",
            str(audio_dir),
            "--model.sample_rate",
            "22050",
            "--data.espeak_voice",
            "ja",
            "--data.cache_dir",
            str(cache_dir),
            "--data.config_path",
            str(config_path),
            "--data.batch_size",
            str(config.batch_size),
            "--model.learning_rate",
            str(config.learning_rate),
            "--trainer.max_epochs",
            str(config.max_epochs),
            "--data.validation_split",
            str(config.validation_split),
            "--trainer.check_val_every_n_epoch",
            str(config.checkpoint_epochs),
            # Note: gradient_clip_val removed because Piper uses manual optimization
            # which doesn't support automatic gradient clipping in PyTorch Lightning
            "--trainer.accelerator",
            config.accelerator.value,
            "--data.phoneme_type",
            "text",  # Use text phonemes from metadata_phonemes.csv
        ]

        # MPS (Apple Silicon) has issues with multiprocessing in dataloaders
        # Set num_workers=0 to disable multiprocessing and prevent semaphore leaks
        if config.accelerator.value == "mps":
            logger.info("Disabling dataloader workers for MPS stability")
            cmd.extend(["--data.num_workers", "0"])

        # Add resume checkpoint if provided
        if resume_checkpoint:
            cmd.extend(["--ckpt_path", str(resume_checkpoint)])

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

        # Read stdout
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

        # Wait for process to complete and capture any remaining output
        return_code = process.wait()

        # Log stderr if training failed
        if return_code != 0 and process.stderr:
            stderr_output = process.stderr.read()
            if stderr_output:
                logger.error(f"Training failed with stderr:\n{stderr_output}")
            training_run.fail()
        else:
            training_run.complete()
