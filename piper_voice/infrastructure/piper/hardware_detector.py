"""Hardware detection for training acceleration."""

import logging

from piper_voice.core.value_objects import HardwareAccelerator

logger = logging.getLogger(__name__)


class HardwareDetector:
    """Detects available hardware acceleration for training."""

    def detect(self) -> HardwareAccelerator:
        """Detect best available hardware accelerator.

        Returns:
            HardwareAccelerator enum (GPU > MPS > CPU)
        """
        try:
            import torch

            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"Detected CUDA GPU: {device_name}")
                return HardwareAccelerator.GPU

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("Detected Apple Silicon (MPS)")
                return HardwareAccelerator.MPS

        except ImportError:
            logger.warning("PyTorch not available, falling back to CPU")

        logger.info("Using CPU (no GPU/MPS detected)")
        return HardwareAccelerator.CPU
