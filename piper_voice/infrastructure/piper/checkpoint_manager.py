"""Checkpoint management for training."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages training checkpoints."""

    def __init__(self, checkpoint_dir: Path):
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory containing checkpoints
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def find_latest_checkpoint(self) -> Path | None:
        """Find the latest checkpoint in directory.

        Returns:
            Path to latest checkpoint or None if no checkpoints found
        """
        checkpoints = list(self.checkpoint_dir.glob("epoch*.ckpt"))
        if not checkpoints:
            return None

        # Sort by modification time (newest first)
        checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return checkpoints[0]

    def find_base_checkpoint(self) -> Path | None:
        """Find base checkpoint for transfer learning.

        Returns:
            Path to base_model.ckpt or None if not found
        """
        base_checkpoint = self.checkpoint_dir / "base_model.ckpt"
        if base_checkpoint.exists():
            return base_checkpoint
        return None

    def validate_checkpoint(self, checkpoint_path: Path) -> bool:
        """Validate checkpoint file exists and is not corrupted.

        Args:
            checkpoint_path: Path to checkpoint file

        Returns:
            True if valid, False otherwise
        """
        if not checkpoint_path.exists():
            logger.error(f"Checkpoint not found: {checkpoint_path}")
            return False

        # Basic size check (should be > 100MB for valid checkpoint)
        size_mb = checkpoint_path.stat().st_size / (1024 * 1024)
        if size_mb < 100:
            logger.warning(f"Checkpoint suspiciously small: {size_mb:.1f}MB")
            return False

        return True
