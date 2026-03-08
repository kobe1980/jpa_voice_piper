"""Unit tests for TrainingConfig value object.

Following TDD: These tests are written BEFORE implementation.
Tests the training configuration value object.
"""

import pytest

from piper_voice.core.value_objects import HardwareAccelerator, TrainingConfig


class TestHardwareAccelerator:
    """Tests for HardwareAccelerator enum."""

    def test_hardware_accelerator_values(self) -> None:
        """Test that hardware accelerator has expected values."""
        assert HardwareAccelerator.GPU.value == "gpu"
        assert HardwareAccelerator.MPS.value == "mps"
        assert HardwareAccelerator.CPU.value == "cpu"


class TestTrainingConfig:
    """Tests for TrainingConfig value object."""

    def test_config_creation_with_defaults(self) -> None:
        """Test creating config with default values."""
        config = TrainingConfig()

        assert config.batch_size == 32
        assert config.learning_rate == 1e-4
        assert config.max_epochs == 1000
        assert config.validation_split == 0.1
        assert config.checkpoint_epochs == 50
        assert config.gradient_clip_val == 1.0
        assert config.accelerator == HardwareAccelerator.GPU

    def test_config_creation_with_custom_values(self) -> None:
        """Test creating config with custom values."""
        config = TrainingConfig(
            batch_size=64,
            learning_rate=2e-4,
            max_epochs=500,
            validation_split=0.2,
            checkpoint_epochs=25,
            gradient_clip_val=0.5,
            accelerator=HardwareAccelerator.CPU,
        )

        assert config.batch_size == 64
        assert config.learning_rate == 2e-4
        assert config.max_epochs == 500
        assert config.validation_split == 0.2
        assert config.checkpoint_epochs == 25
        assert config.gradient_clip_val == 0.5
        assert config.accelerator == HardwareAccelerator.CPU

    def test_config_validates_batch_size(self) -> None:
        """Test that batch size is validated."""
        with pytest.raises(ValueError, match="Batch size must be between"):
            TrainingConfig(batch_size=0)

        with pytest.raises(ValueError, match="Batch size must be between"):
            TrainingConfig(batch_size=256)

    def test_config_validates_learning_rate(self) -> None:
        """Test that learning rate is validated."""
        with pytest.raises(ValueError, match="Learning rate must be between"):
            TrainingConfig(learning_rate=0.0)

        with pytest.raises(ValueError, match="Learning rate must be between"):
            TrainingConfig(learning_rate=1.0)

    def test_config_validates_max_epochs(self) -> None:
        """Test that max epochs is validated."""
        with pytest.raises(ValueError, match="Max epochs must be between"):
            TrainingConfig(max_epochs=0)

        with pytest.raises(ValueError, match="Max epochs must be between"):
            TrainingConfig(max_epochs=20000)

    def test_config_validates_validation_split(self) -> None:
        """Test that validation split is validated."""
        with pytest.raises(ValueError, match="Validation split must be between"):
            TrainingConfig(validation_split=0.0)

        with pytest.raises(ValueError, match="Validation split must be between"):
            TrainingConfig(validation_split=0.5)

    def test_config_validates_checkpoint_epochs(self) -> None:
        """Test that checkpoint epochs is validated."""
        with pytest.raises(ValueError, match="Checkpoint epochs must be between"):
            TrainingConfig(checkpoint_epochs=0)

        with pytest.raises(ValueError, match="Checkpoint epochs must be between"):
            TrainingConfig(checkpoint_epochs=200)

    def test_config_is_frozen(self) -> None:
        """Test that config is immutable."""
        config = TrainingConfig()

        with pytest.raises(Exception) as exc_info:  # FrozenInstanceError
            config.batch_size = 64  # type: ignore
        assert "frozen" in str(exc_info.value).lower() or "cannot" in str(
            exc_info.value
        ).lower()

    def test_config_for_gpu_factory(self) -> None:
        """Test factory method for GPU config."""
        config = TrainingConfig.for_gpu()

        assert config.accelerator == HardwareAccelerator.GPU
        assert config.batch_size == 32

    def test_config_for_mps_factory(self) -> None:
        """Test factory method for MPS (Apple Silicon) config."""
        config = TrainingConfig.for_mps()

        assert config.accelerator == HardwareAccelerator.MPS
        assert config.batch_size == 16  # Smaller for MPS

    def test_config_for_cpu_factory(self) -> None:
        """Test factory method for CPU config."""
        config = TrainingConfig.for_cpu()

        assert config.accelerator == HardwareAccelerator.CPU
        assert config.batch_size == 8  # Smaller for CPU

    def test_config_for_fast_experiment_factory(self) -> None:
        """Test factory method for fast experiment."""
        config = TrainingConfig.for_fast_experiment()

        assert config.max_epochs == 100
        assert config.checkpoint_epochs == 10

    def test_config_for_high_quality_factory(self) -> None:
        """Test factory method for high quality training."""
        config = TrainingConfig.for_high_quality()

        assert config.max_epochs == 5000
        assert config.learning_rate == 5e-5
        assert config.checkpoint_epochs == 100
