# ADR-005: Piper Training Integration

**Status**: ACCEPTED
**Date**: 2026-03-08
**Deciders**: Architect
**Related**: STORY-005-piper-training-integration.md, ADR-001-japanese-voice-architecture.md, ADR-004-piper-preprocessing-integration.md

---

## Context

STORY-005 requires integrating with Piper's training pipeline to train a Japanese TTS voice model from preprocessed dataset. This is the culminating phase that transforms prepared data into a working voice model.

**Key Challenges**:

1. **Long-Running Process**: Training takes hours to days (must be interruptible and resumable)
2. **Training Wrapper Strategy**: How to invoke PyTorch Lightning-based Piper training safely
3. **Progress Monitoring**: Real-time loss tracking without blocking execution
4. **Checkpoint Management**: Save/resume/recover from training state
5. **Transfer Learning**: Load base checkpoints for faster convergence
6. **Hardware Abstraction**: GPU/MPS/CPU detection and configuration
7. **Error Handling**: Graceful recovery from crashes, OOM errors, interruptions
8. **DDD Architecture**: Maintain domain/application/infrastructure boundaries

**Technical Constraints**:
- Input: `training/dataset.jsonl`, `training/config.json`, `training/audio_norm_stats.json` (from Phase 4)
- Output: `checkpoints/*.ckpt`, `lightning_logs/`, `models/*.onnx` (final export)
- Requirement: Compatible with Piper VITS architecture and PyTorch Lightning
- Performance: Must support batch sizes 16-64, checkpoint every 1-100 epochs
- Resumption: Must preserve exact training state (optimizer, epoch, losses)

**Architectural Requirements** (from CLAUDE.md):
- Domain layer (`piper_voice/core`) must NOT depend on infrastructure
- Infrastructure adapters must be injected via ports
- TDD mandatory: tests before implementation
- Security: path validation, checkpoint size limits, disk space monitoring, timeout for runaway training

---

## Decisions

### 1. Training Wrapper Strategy: Subprocess with Progress Monitoring

**Decision**: Use subprocess wrapper for Piper training with non-blocking progress monitoring.

**Architecture**:
```
piper_voice/
├── core/
│   ├── entities.py
│   │   └── TrainingRun (new entity: represents training session state)
│   ├── value_objects.py
│   │   └── TrainingConfig (new value object: training hyperparameters)
│   │   └── HardwareAccelerator (new value object: GPU/MPS/CPU)
│   └── ports.py
│       └── PiperTrainingPort (already exists, update with train_voice signature)
│
├── infrastructure/
│   └── piper/
│       ├── training_adapter.py (new: implements PiperTrainingPort.train_voice)
│       ├── checkpoint_manager.py (new: checkpoint save/load/validation)
│       └── progress_monitor.py (new: TensorBoard log parsing for progress)
│
└── application/
    └── train_japanese_voice.py (new: orchestration use case)
```

**Integration Approach**:

**Option A - Subprocess Wrapper with Progress Monitoring** (CHOSEN):
```python
# infrastructure/piper/training_adapter.py
import subprocess
import threading
from pathlib import Path

class PiperTrainingAdapter:
    """Adapter for Piper training operations via subprocess."""
    
    def train_voice(
        self,
        dataset_dir: Path,
        checkpoint_dir: Path,
        config: TrainingConfig,
        base_checkpoint: Path | None = None,
        resume_checkpoint: Path | None = None
    ) -> TrainingRun:
        """Start Piper training in subprocess with progress monitoring.
        
        Args:
            dataset_dir: Directory with dataset.jsonl, config.json
            checkpoint_dir: Directory to save checkpoints
            config: Training hyperparameters
            base_checkpoint: Optional base model for transfer learning
            resume_checkpoint: Optional checkpoint to resume from
            
        Returns:
            TrainingRun entity with training session state
            
        Raises:
            FileNotFoundError: If required files missing
            ValueError: If training fails to start
        """
        # Build piper_train command
        cmd = [
            "python", "-m", "piper_train",
            "--dataset-dir", str(dataset_dir),
            "--accelerator", config.accelerator.value,
            "--devices", str(config.devices),
            "--batch-size", str(config.batch_size),
            "--learning-rate", str(config.learning_rate),
            "--max_epochs", str(config.max_epochs),
            "--validation-split", str(config.validation_split),
            "--checkpoint-epochs", str(config.checkpoint_epochs),
            "--precision", str(config.precision),
            "--gradient-clip-val", str(config.gradient_clip_val),
        ]
        
        # Add base checkpoint for transfer learning
        if base_checkpoint:
            cmd.extend(["--resume_from_checkpoint", str(base_checkpoint)])
        
        # Add resume checkpoint
        if resume_checkpoint:
            cmd.extend(["--resume_from_checkpoint", str(resume_checkpoint)])
        
        # Start training process (non-blocking)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line-buffered
        )
        
        # Create training run entity
        training_run = TrainingRun(
            id=f"training_{int(time.time())}",
            process_id=process.pid,
            dataset_dir=dataset_dir,
            checkpoint_dir=checkpoint_dir,
            config=config,
            status=TrainingStatus.RUNNING,
            start_time=datetime.now()
        )
        
        # Start progress monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_progress,
            args=(process, training_run),
            daemon=True
        )
        monitor_thread.start()
        
        return training_run
```

**Rationale**:
- ✅ Isolation: Training crashes don't crash application
- ✅ Standard Interface: Uses Piper's official CLI
- ✅ Interruptible: Can send SIGINT/SIGTERM to process
- ✅ Non-Blocking: Application remains responsive during training
- ✅ Progress Tracking: Monitor stdout/stderr for loss updates
- ❌ Subprocess Overhead: Minimal (one-time startup cost)
- ❌ Communication: Parse logs for progress (not ideal but works)

**Option B - Python API Direct Import** (Rejected):
```python
# Would require:
from piper_train.train import train_model
from pytorch_lightning import Trainer

# Problem: Blocks Python process for hours/days
# Problem: Difficult to interrupt gracefully
# Problem: Tight coupling to Piper internal API
```

**Rationale for Rejection**:
- ❌ Blocking: Would block entire application during training
- ❌ Interruption: Hard to gracefully stop mid-training
- ❌ Coupling: Breaks if Piper internals change
- ❌ Error Handling: Exceptions propagate to application

**Final Decision**: Use **Option A (Subprocess Wrapper)** for isolation, interruptibility, and standard interface compliance.

---

### 2. Training Configuration: Value Object with Validation

**Decision**: Model training hyperparameters as immutable value object with validation.

**Value Object Definition** (`piper_voice/core/value_objects.py`):
```python
from dataclasses import dataclass
from enum import Enum

class HardwareAccelerator(str, Enum):
    """Hardware accelerator types."""
    GPU = "gpu"      # CUDA (NVIDIA)
    MPS = "mps"      # Apple Silicon
    CPU = "cpu"      # CPU fallback

@dataclass(frozen=True)
class TrainingConfig:
    """Training hyperparameters value object.
    
    Defines sensible defaults and validates ranges.
    """
    
    # Core training parameters
    batch_size: int = 32
    learning_rate: float = 1e-4
    max_epochs: int = 1000
    
    # Validation and checkpointing
    validation_split: float = 0.1
    checkpoint_epochs: int = 10
    
    # Hardware configuration
    accelerator: HardwareAccelerator = HardwareAccelerator.GPU
    devices: int = 1
    
    # Optimization parameters
    precision: int = 32
    gradient_clip_val: float = 1.0
    
    # Early stopping (optional)
    early_stopping_patience: int | None = None  # None = no early stopping
    
    def __post_init__(self) -> None:
        """Validate training configuration."""
        # Batch size
        if not (1 <= self.batch_size <= 128):
            raise ValueError(f"Batch size must be 1-128, got {self.batch_size}")
        
        # Learning rate
        if not (1e-6 <= self.learning_rate <= 1e-2):
            raise ValueError(
                f"Learning rate must be 1e-6 to 1e-2, got {self.learning_rate}"
            )
        
        # Max epochs
        if not (1 <= self.max_epochs <= 10000):
            raise ValueError(f"Max epochs must be 1-10000, got {self.max_epochs}")
        
        # Validation split
        if not (0.01 <= self.validation_split <= 0.5):
            raise ValueError(
                f"Validation split must be 0.01-0.5, got {self.validation_split}"
            )
        
        # Checkpoint frequency
        if not (1 <= self.checkpoint_epochs <= 1000):
            raise ValueError(
                f"Checkpoint epochs must be 1-1000, got {self.checkpoint_epochs}"
            )
        
        # Precision
        if self.precision not in (16, 32):
            raise ValueError(f"Precision must be 16 or 32, got {self.precision}")
        
        # Gradient clipping
        if not (0.1 <= self.gradient_clip_val <= 10.0):
            raise ValueError(
                f"Gradient clip must be 0.1-10.0, got {self.gradient_clip_val}"
            )
        
        # Early stopping patience
        if self.early_stopping_patience is not None:
            if self.early_stopping_patience < 1:
                raise ValueError("Early stopping patience must be >= 1")

    @classmethod
    def default_gpu(cls) -> "TrainingConfig":
        """Factory: Default config for GPU training."""
        return cls(
            batch_size=32,
            learning_rate=1e-4,
            max_epochs=1000,
            accelerator=HardwareAccelerator.GPU,
            checkpoint_epochs=10
        )
    
    @classmethod
    def default_mps(cls) -> "TrainingConfig":
        """Factory: Default config for Apple Silicon MPS."""
        return cls(
            batch_size=16,  # MPS has less memory
            learning_rate=1e-4,
            max_epochs=1000,
            accelerator=HardwareAccelerator.MPS,
            checkpoint_epochs=10
        )
    
    @classmethod
    def default_cpu(cls) -> "TrainingConfig":
        """Factory: Default config for CPU (slow)."""
        return cls(
            batch_size=8,   # CPU is slow, use small batch
            learning_rate=1e-4,
            max_epochs=100,  # Limit epochs for CPU
            accelerator=HardwareAccelerator.CPU,
            checkpoint_epochs=5
        )
    
    @classmethod
    def fast_experiment(cls, accelerator: HardwareAccelerator) -> "TrainingConfig":
        """Factory: Fast config for experimentation."""
        return cls(
            batch_size=64,
            learning_rate=1e-3,  # Higher LR for faster convergence
            max_epochs=100,
            accelerator=accelerator,
            checkpoint_epochs=5,
            early_stopping_patience=20
        )
    
    @classmethod
    def high_quality(cls, accelerator: HardwareAccelerator) -> "TrainingConfig":
        """Factory: High-quality config for production."""
        return cls(
            batch_size=32,
            learning_rate=5e-5,  # Lower LR for stability
            max_epochs=5000,
            accelerator=accelerator,
            checkpoint_epochs=50,
            early_stopping_patience=200
        )
```

**Rationale**:
- ✅ Immutable: Cannot be accidentally modified during training
- ✅ Validated: All parameters checked at creation time
- ✅ Domain Logic: Validation rules are business constraints
- ✅ Factory Methods: Sensible defaults for different scenarios
- ✅ Type Safety: Enum for accelerator prevents typos

---

### 3. Training State Management: TrainingRun Entity

**Decision**: Model training session as entity with lifecycle and state transitions.

**Entity Definition** (`piper_voice/core/entities.py`):
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

class TrainingStatus(str, Enum):
    """Training status states."""
    PENDING = "pending"           # Not started yet
    RUNNING = "running"           # Currently training
    PAUSED = "paused"             # Paused by user
    COMPLETED = "completed"       # Finished successfully
    FAILED = "failed"             # Failed with error
    INTERRUPTED = "interrupted"   # Stopped by user (Ctrl+C)

@dataclass
class TrainingMetrics:
    """Training metrics snapshot."""
    current_epoch: int
    total_epochs: int
    train_loss: float
    validation_loss: float | None
    learning_rate: float
    samples_per_second: float | None
    
    def progress_percentage(self) -> float:
        """Calculate training progress percentage."""
        if self.total_epochs == 0:
            return 0.0
        return (self.current_epoch / self.total_epochs) * 100

@dataclass
class TrainingRun:
    """Training run entity.
    
    Represents a single training session with state and lifecycle.
    """
    
    id: str
    process_id: int | None
    dataset_dir: Path
    checkpoint_dir: Path
    config: TrainingConfig
    status: TrainingStatus
    start_time: datetime
    
    # Optional fields
    end_time: datetime | None = None
    current_metrics: TrainingMetrics | None = None
    error_message: str | None = None
    best_checkpoint_path: Path | None = None
    latest_checkpoint_path: Path | None = None
    
    # History
    checkpoints: list[Path] = field(default_factory=list)
    
    def mark_completed(self, best_checkpoint: Path) -> None:
        """Mark training as completed successfully.
        
        Args:
            best_checkpoint: Path to best checkpoint (lowest validation loss)
        """
        self.status = TrainingStatus.COMPLETED
        self.end_time = datetime.now()
        self.best_checkpoint_path = best_checkpoint
    
    def mark_failed(self, error: str) -> None:
        """Mark training as failed with error message.
        
        Args:
            error: Error message describing failure
        """
        self.status = TrainingStatus.FAILED
        self.end_time = datetime.now()
        self.error_message = error
    
    def mark_interrupted(self) -> None:
        """Mark training as interrupted by user."""
        self.status = TrainingStatus.INTERRUPTED
        self.end_time = datetime.now()
    
    def add_checkpoint(self, checkpoint_path: Path) -> None:
        """Record a new checkpoint.
        
        Args:
            checkpoint_path: Path to saved checkpoint
        """
        self.checkpoints.append(checkpoint_path)
        self.latest_checkpoint_path = checkpoint_path
    
    def update_metrics(self, metrics: TrainingMetrics) -> None:
        """Update current training metrics.
        
        Args:
            metrics: Latest training metrics
        """
        self.current_metrics = metrics
    
    def duration_seconds(self) -> float | None:
        """Calculate training duration in seconds.
        
        Returns:
            Duration in seconds, or None if not finished
        """
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    def is_active(self) -> bool:
        """Check if training is currently active.
        
        Returns:
            True if training is running or paused
        """
        return self.status in (TrainingStatus.RUNNING, TrainingStatus.PAUSED)
    
    def can_resume(self) -> bool:
        """Check if training can be resumed.
        
        Returns:
            True if training was interrupted and has checkpoints
        """
        return (
            self.status in (TrainingStatus.INTERRUPTED, TrainingStatus.PAUSED)
            and self.latest_checkpoint_path is not None
        )
```

**Rationale**:
- ✅ State Machine: Clear status transitions
- ✅ Lifecycle Management: Track from start to completion
- ✅ Metrics Tracking: Store current training progress
- ✅ Checkpoint History: Record all saved checkpoints
- ✅ Resumability: Check if training can be resumed
- ✅ Domain Entity: Has identity (id) and mutable state

---

### 4. Checkpoint Management: Safety and Validation

**Decision**: Implement checkpoint manager with validation, size limits, and recovery.

**Checkpoint Manager** (`infrastructure/piper/checkpoint_manager.py`):
```python
from pathlib import Path
from typing import Optional
import shutil
import json

class CheckpointManager:
    """Manages training checkpoint save/load/validation."""
    
    MAX_CHECKPOINT_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB per checkpoint
    MAX_TOTAL_CHECKPOINTS = 20  # Limit total checkpoints to save disk
    
    def __init__(self, checkpoint_dir: Path):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_checkpoint(self, checkpoint_path: Path) -> tuple[bool, str | None]:
        """Validate checkpoint file.
        
        Args:
            checkpoint_path: Path to checkpoint file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check exists
        if not checkpoint_path.exists():
            return False, f"Checkpoint not found: {checkpoint_path}"
        
        # Check file extension
        if checkpoint_path.suffix != ".ckpt":
            return False, f"Invalid checkpoint extension: {checkpoint_path.suffix}"
        
        # Check size
        file_size = checkpoint_path.stat().st_size
        if file_size > self.MAX_CHECKPOINT_SIZE:
            return False, (
                f"Checkpoint too large: {file_size / 1e9:.2f} GB "
                f"(max {self.MAX_CHECKPOINT_SIZE / 1e9:.2f} GB)"
            )
        
        # Check not empty
        if file_size == 0:
            return False, "Checkpoint file is empty"
        
        # Check readable (basic corruption test)
        try:
            # PyTorch checkpoints are just ZIP files, try to open
            import torch
            checkpoint = torch.load(checkpoint_path, map_location="cpu")
            
            # Check required keys
            required_keys = ["state_dict", "epoch"]
            for key in required_keys:
                if key not in checkpoint:
                    return False, f"Checkpoint missing required key: {key}"
            
            return True, None
        except Exception as e:
            return False, f"Checkpoint corrupted or unreadable: {e}"
    
    def find_latest_checkpoint(self) -> Path | None:
        """Find latest checkpoint in directory.
        
        Returns:
            Path to latest checkpoint, or None if no checkpoints found
        """
        checkpoints = sorted(
            self.checkpoint_dir.glob("*.ckpt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not checkpoints:
            return None
        
        return checkpoints[0]
    
    def find_best_checkpoint(self) -> Path | None:
        """Find best checkpoint (lowest validation loss).
        
        Lightning saves best checkpoint with 'val_loss' in name.
        
        Returns:
            Path to best checkpoint, or None if not found
        """
        # Lightning naming convention
        best_candidates = list(self.checkpoint_dir.glob("**/best*.ckpt"))
        if best_candidates:
            return best_candidates[0]
        
        # Fallback: look for explicit val_loss in filename
        val_loss_checkpoints = []
        for ckpt in self.checkpoint_dir.glob("**/*.ckpt"):
            if "val_loss" in ckpt.name:
                val_loss_checkpoints.append(ckpt)
        
        if val_loss_checkpoints:
            # Sort by modification time (latest is often best)
            return sorted(
                val_loss_checkpoints,
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[0]
        
        return None
    
    def list_checkpoints(self) -> list[Path]:
        """List all checkpoints in directory.
        
        Returns:
            List of checkpoint paths, sorted by modification time (newest first)
        """
        checkpoints = sorted(
            self.checkpoint_dir.glob("**/*.ckpt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return checkpoints
    
    def cleanup_old_checkpoints(self, keep_count: int = 10) -> int:
        """Remove old checkpoints to save disk space.
        
        Keeps the N most recent checkpoints, plus any 'best' checkpoints.
        
        Args:
            keep_count: Number of recent checkpoints to keep
            
        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints()
        
        # Separate best checkpoints (never delete)
        best_checkpoints = {ckpt for ckpt in checkpoints if "best" in ckpt.name.lower()}
        regular_checkpoints = [ckpt for ckpt in checkpoints if ckpt not in best_checkpoints]
        
        # Delete old regular checkpoints
        deleted_count = 0
        for checkpoint in regular_checkpoints[keep_count:]:
            try:
                checkpoint.unlink()
                deleted_count += 1
            except Exception as e:
                # Log but don't fail
                print(f"Warning: Could not delete checkpoint {checkpoint}: {e}")
        
        return deleted_count
    
    def estimate_disk_usage(self) -> int:
        """Estimate total disk usage of all checkpoints.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        for checkpoint in self.list_checkpoints():
            total_size += checkpoint.stat().st_size
        return total_size
    
    def copy_base_checkpoint(
        self,
        source_checkpoint: Path,
        target_name: str = "base_model.ckpt"
    ) -> Path:
        """Copy base checkpoint to training directory.
        
        Args:
            source_checkpoint: Path to base checkpoint
            target_name: Target filename
            
        Returns:
            Path to copied checkpoint
            
        Raises:
            FileNotFoundError: If source checkpoint doesn't exist
            ValueError: If checkpoint invalid
        """
        # Validate source
        is_valid, error = self.validate_checkpoint(source_checkpoint)
        if not is_valid:
            raise ValueError(f"Invalid base checkpoint: {error}")
        
        # Copy to checkpoint directory
        target_path = self.checkpoint_dir / target_name
        shutil.copy2(source_checkpoint, target_path)
        
        return target_path
```

**Rationale**:
- ✅ Validation: Detects corrupted checkpoints early
- ✅ Size Limits: Prevents disk exhaustion
- ✅ Discovery: Find latest/best checkpoints automatically
- ✅ Cleanup: Remove old checkpoints to save space
- ✅ Safety: Never deletes 'best' checkpoints
- ✅ Base Checkpoint Handling: Copy external checkpoints safely

---

### 5. Progress Monitoring: Real-Time Loss Tracking

**Decision**: Parse training logs for real-time progress without blocking.

**Progress Monitor** (`infrastructure/piper/progress_monitor.py`):
```python
import re
from pathlib import Path
from typing import Optional, Callable
import threading
import time

class ProgressMonitor:
    """Monitors training progress by parsing logs and TensorBoard events."""
    
    # Regex patterns for parsing Lightning logs
    EPOCH_PATTERN = re.compile(r"Epoch (\d+)/(\d+)")
    LOSS_PATTERN = re.compile(r"train_loss=([0-9.]+)")
    VAL_LOSS_PATTERN = re.compile(r"val_loss=([0-9.]+)")
    LR_PATTERN = re.compile(r"lr=([0-9.e-]+)")
    
    def __init__(
        self,
        lightning_logs_dir: Path,
        callback: Optional[Callable[[TrainingMetrics], None]] = None
    ):
        """Initialize progress monitor.
        
        Args:
            lightning_logs_dir: Directory with Lightning logs
            callback: Optional callback to invoke on metrics update
        """
        self.lightning_logs_dir = lightning_logs_dir
        self.callback = callback
        self._stop_event = threading.Event()
    
    def parse_log_line(self, line: str) -> TrainingMetrics | None:
        """Parse a single log line for metrics.
        
        Args:
            line: Log line to parse
            
        Returns:
            TrainingMetrics if line contains metrics, else None
        """
        # Parse epoch
        epoch_match = self.EPOCH_PATTERN.search(line)
        if not epoch_match:
            return None
        
        current_epoch = int(epoch_match.group(1))
        total_epochs = int(epoch_match.group(2))
        
        # Parse losses
        train_loss_match = self.LOSS_PATTERN.search(line)
        if not train_loss_match:
            return None
        
        train_loss = float(train_loss_match.group(1))
        
        val_loss_match = self.VAL_LOSS_PATTERN.search(line)
        val_loss = float(val_loss_match.group(1)) if val_loss_match else None
        
        # Parse learning rate
        lr_match = self.LR_PATTERN.search(line)
        learning_rate = float(lr_match.group(1)) if lr_match else 1e-4
        
        return TrainingMetrics(
            current_epoch=current_epoch,
            total_epochs=total_epochs,
            train_loss=train_loss,
            validation_loss=val_loss,
            learning_rate=learning_rate,
            samples_per_second=None  # Not always available
        )
    
    def monitor_training(self, training_run: TrainingRun) -> None:
        """Monitor training progress continuously.
        
        Runs in background thread, updates training_run metrics.
        
        Args:
            training_run: TrainingRun entity to update
        """
        # Find latest version directory
        version_dirs = sorted(self.lightning_logs_dir.glob("version_*"))
        if not version_dirs:
            return
        
        latest_version = version_dirs[-1]
        log_file = latest_version / "metrics.csv"
        
        # Wait for log file to be created
        while not log_file.exists() and not self._stop_event.is_set():
            time.sleep(1)
        
        # Tail log file
        with open(log_file) as f:
            # Skip to end
            f.seek(0, 2)
            
            while not self._stop_event.is_set():
                line = f.readline()
                
                if not line:
                    # No new data, wait
                    time.sleep(1)
                    continue
                
                # Parse metrics
                metrics = self.parse_log_line(line)
                if metrics:
                    training_run.update_metrics(metrics)
                    
                    # Invoke callback
                    if self.callback:
                        self.callback(metrics)
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._stop_event.set()
```

**Rationale**:
- ✅ Non-Blocking: Runs in background thread
- ✅ Real-Time: Updates metrics as training progresses
- ✅ Callback Support: Notify application of progress
- ✅ Log Parsing: Extracts metrics from Lightning logs
- ✅ Graceful Stop: Can be interrupted cleanly

---

### 6. Hardware Detection: Automatic Accelerator Selection

**Decision**: Detect available hardware and auto-configure training.

**Hardware Detector** (`infrastructure/piper/hardware_detector.py`):
```python
import platform
from piper_voice.core.value_objects import HardwareAccelerator

class HardwareDetector:
    """Detects available hardware accelerators for training."""
    
    @staticmethod
    def detect_best_accelerator() -> HardwareAccelerator:
        """Detect best available hardware accelerator.
        
        Priority: GPU (CUDA) > MPS (Apple Silicon) > CPU
        
        Returns:
            Best available accelerator
        """
        # Check for CUDA GPU
        if HardwareDetector._has_cuda():
            return HardwareAccelerator.GPU
        
        # Check for Apple Silicon MPS
        if HardwareDetector._has_mps():
            return HardwareAccelerator.MPS
        
        # Fallback to CPU
        return HardwareAccelerator.CPU
    
    @staticmethod
    def _has_cuda() -> bool:
        """Check if CUDA GPU is available.
        
        Returns:
            True if CUDA available
        """
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    @staticmethod
    def _has_mps() -> bool:
        """Check if Apple Silicon MPS is available.
        
        Returns:
            True if MPS available (macOS with M1/M2/M3)
        """
        # MPS only available on macOS
        if platform.system() != "Darwin":
            return False
        
        try:
            import torch
            return torch.backends.mps.is_available()
        except (ImportError, AttributeError):
            return False
    
    @staticmethod
    def get_device_count(accelerator: HardwareAccelerator) -> int:
        """Get number of devices for accelerator.
        
        Args:
            accelerator: Hardware accelerator type
            
        Returns:
            Number of devices (GPUs, CPU cores, etc.)
        """
        if accelerator == HardwareAccelerator.GPU:
            try:
                import torch
                return torch.cuda.device_count()
            except ImportError:
                return 0
        
        elif accelerator == HardwareAccelerator.MPS:
            # MPS always has 1 device (the Apple Silicon GPU)
            return 1 if HardwareDetector._has_mps() else 0
        
        else:  # CPU
            import os
            return os.cpu_count() or 1
    
    @staticmethod
    def get_device_name(accelerator: HardwareAccelerator) -> str:
        """Get human-readable device name.
        
        Args:
            accelerator: Hardware accelerator type
            
        Returns:
            Device name string
        """
        if accelerator == HardwareAccelerator.GPU:
            try:
                import torch
                if torch.cuda.is_available():
                    return torch.cuda.get_device_name(0)
                return "CUDA (not available)"
            except ImportError:
                return "CUDA (PyTorch not installed)"
        
        elif accelerator == HardwareAccelerator.MPS:
            if HardwareDetector._has_mps():
                return "Apple Silicon GPU (MPS)"
            return "MPS (not available)"
        
        else:  # CPU
            return f"CPU ({platform.processor()})"
```

**Rationale**:
- ✅ Automatic Detection: No manual configuration needed
- ✅ Graceful Fallback: Falls back to CPU if GPU unavailable
- ✅ Device Information: Reports device name for user feedback
- ✅ Cross-Platform: Works on macOS (MPS), Linux/Windows (CUDA), all (CPU)

---

### 7. Application Orchestration: Complete Training Pipeline

**Decision**: Application layer orchestrates training with validation and monitoring.

**Use Case Implementation** (`piper_voice/application/train_japanese_voice.py`):
```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

from piper_voice.core.entities import TrainingRun, TrainingStatus
from piper_voice.core.value_objects import TrainingConfig, HardwareAccelerator
from piper_voice.core.ports import FileSystemPort
from piper_voice.infrastructure.piper.training_adapter import PiperTrainingAdapter
from piper_voice.infrastructure.piper.checkpoint_manager import CheckpointManager
from piper_voice.infrastructure.piper.hardware_detector import HardwareDetector
from piper_voice.infrastructure.piper.progress_monitor import ProgressMonitor

@dataclass
class TrainingResult:
    """Result of training operation."""
    training_run: TrainingRun
    success: bool
    best_checkpoint: Path | None
    error: str | None = None

def train_japanese_voice(
    dataset_dir: Path,
    checkpoint_dir: Path,
    config: Optional[TrainingConfig] = None,
    base_checkpoint: Optional[Path] = None,
    resume_checkpoint: Optional[Path] = None,
    filesystem: Optional[FileSystemPort] = None,
    logger: Optional[logging.Logger] = None
) -> TrainingResult:
    """Train Japanese TTS voice model.
    
    Complete training pipeline:
    1. Validate inputs (dataset.jsonl, config.json exist)
    2. Detect hardware and auto-configure if needed
    3. Validate base checkpoint if provided
    4. Start training with Piper
    5. Monitor progress
    6. Wait for completion or handle interruption
    7. Validate final checkpoint
    
    Args:
        dataset_dir: Directory with preprocessed data (from Phase 4)
        checkpoint_dir: Directory to save checkpoints
        config: Training configuration (auto-detected if None)
        base_checkpoint: Optional base checkpoint for transfer learning
        resume_checkpoint: Optional checkpoint to resume from
        filesystem: Optional filesystem adapter for path validation
        logger: Optional logger
        
    Returns:
        TrainingResult with training outcome
        
    Raises:
        FileNotFoundError: If required input files missing
        ValueError: If training fails to start
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Phase 1: Validate inputs
    logger.info("Validating training inputs...")
    
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    dataset_jsonl = dataset_dir / "dataset.jsonl"
    config_json = dataset_dir / "config.json"
    audio_stats = dataset_dir / "audio_norm_stats.json"
    
    required_files = [dataset_jsonl, config_json, audio_stats]
    for required_file in required_files:
        if not required_file.exists():
            raise FileNotFoundError(f"Required file not found: {required_file}")
    
    # Validate checkpoint directory is allowed
    if filesystem and not filesystem.is_path_allowed(checkpoint_dir):
        raise PermissionError(f"Checkpoint directory not allowed: {checkpoint_dir}")
    
    # Create checkpoint directory
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Phase 2: Auto-detect hardware if config not provided
    if config is None:
        logger.info("Auto-detecting hardware configuration...")
        accelerator = HardwareDetector.detect_best_accelerator()
        device_name = HardwareDetector.get_device_name(accelerator)
        logger.info(f"Detected hardware: {device_name}")
        
        # Use appropriate default config
        if accelerator == HardwareAccelerator.GPU:
            config = TrainingConfig.default_gpu()
        elif accelerator == HardwareAccelerator.MPS:
            config = TrainingConfig.default_mps()
        else:
            config = TrainingConfig.default_cpu()
            logger.warning("No GPU/MPS detected, training will be very slow on CPU")
    
    logger.info(f"Training configuration: {config}")
    
    # Phase 3: Initialize checkpoint manager
    checkpoint_manager = CheckpointManager(checkpoint_dir)
    
    # Validate base checkpoint if provided
    if base_checkpoint:
        logger.info(f"Validating base checkpoint: {base_checkpoint}")
        is_valid, error = checkpoint_manager.validate_checkpoint(base_checkpoint)
        if not is_valid:
            raise ValueError(f"Invalid base checkpoint: {error}")
        logger.info("Base checkpoint validated (transfer learning enabled)")
    
    # Validate resume checkpoint if provided
    if resume_checkpoint:
        logger.info(f"Validating resume checkpoint: {resume_checkpoint}")
        is_valid, error = checkpoint_manager.validate_checkpoint(resume_checkpoint)
        if not is_valid:
            raise ValueError(f"Invalid resume checkpoint: {error}")
        logger.info(f"Resuming training from checkpoint: {resume_checkpoint}")
    
    # Phase 4: Start training
    logger.info("Starting Piper training...")
    
    training_adapter = PiperTrainingAdapter()
    
    try:
        training_run = training_adapter.train_voice(
            dataset_dir=dataset_dir,
            checkpoint_dir=checkpoint_dir,
            config=config,
            base_checkpoint=base_checkpoint,
            resume_checkpoint=resume_checkpoint
        )
        
        logger.info(f"Training started (process ID: {training_run.process_id})")
        
        # Phase 5: Monitor progress
        lightning_logs_dir = checkpoint_dir.parent / "lightning_logs"
        progress_monitor = ProgressMonitor(
            lightning_logs_dir=lightning_logs_dir,
            callback=lambda metrics: logger.info(
                f"Epoch {metrics.current_epoch}/{metrics.total_epochs} - "
                f"Loss: {metrics.train_loss:.4f}"
            )
        )
        
        monitor_thread = threading.Thread(
            target=progress_monitor.monitor_training,
            args=(training_run,),
            daemon=True
        )
        monitor_thread.start()
        
        # Phase 6: Wait for completion
        logger.info("Training in progress. Press Ctrl+C to stop.")
        logger.info(f"Monitor progress: tensorboard --logdir {lightning_logs_dir}")
        
        # This is where we would wait for the subprocess to complete
        # In practice, this function might return immediately and let
        # training run in background, with status checked separately
        
        return TrainingResult(
            training_run=training_run,
            success=True,
            best_checkpoint=None,  # Will be set when training completes
            error=None
        )
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return TrainingResult(
            training_run=None,
            success=False,
            best_checkpoint=None,
            error=str(e)
        )
```

**Rationale**:
- ✅ Complete Pipeline: All validation and setup steps
- ✅ Auto-Configuration: Detects hardware automatically
- ✅ Comprehensive Logging: Tracks all operations
- ✅ Error Handling: Graceful failure with context
- ✅ Respects DDD Boundaries: Orchestration in application layer
- ✅ Progress Monitoring: Real-time feedback to user

---

### 8. Security Guardrails: Training Safety Limits

**Decision**: Enforce strict security limits on training operations.

**Security Measures**:

1. **Path Validation** (via FileSystemPort):
```python
ALLOWED_TRAINING_DIRECTORIES = [
    Path("./dataset"),
    Path("./training"),
    Path("./checkpoints"),
    Path("./models"),
    Path("./logs"),
    Path("./lightning_logs")
]
```

2. **Checkpoint Size Limits**:
```python
MAX_CHECKPOINT_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB per checkpoint
MAX_TOTAL_CHECKPOINTS = 20  # Limit total checkpoints
MAX_CHECKPOINT_DIR_SIZE = 100 * 1024 * 1024 * 1024  # 100 GB total
```

3. **Training Timeout** (for safety):
```python
MAX_TRAINING_TIME = 7 * 24 * 3600  # 7 days maximum
```

4. **Disk Space Monitoring**:
```python
def check_disk_space(checkpoint_dir: Path, required_gb: int = 50) -> bool:
    """Check if sufficient disk space available.
    
    Args:
        checkpoint_dir: Checkpoint directory path
        required_gb: Required GB of free space
        
    Returns:
        True if sufficient space available
    """
    stat = shutil.disk_usage(checkpoint_dir)
    free_gb = stat.free / (1024 ** 3)
    return free_gb >= required_gb
```

5. **Memory Monitoring** (detect OOM early):
```python
def check_memory(batch_size: int, accelerator: HardwareAccelerator) -> tuple[bool, str]:
    """Check if sufficient memory for batch size.
    
    Args:
        batch_size: Training batch size
        accelerator: Hardware accelerator
        
    Returns:
        Tuple of (is_sufficient, warning_message)
    """
    if accelerator == HardwareAccelerator.GPU:
        import torch
        if torch.cuda.is_available():
            gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            estimated_batch_memory = batch_size * 0.5  # ~500 MB per sample
            
            if estimated_batch_memory > gpu_memory_gb * 0.8:
                return False, (
                    f"Batch size {batch_size} may exceed GPU memory "
                    f"({gpu_memory_gb:.1f} GB). Try batch_size <= {int(gpu_memory_gb * 0.8 / 0.5)}"
                )
    
    return True, ""
```

**Rationale**:
- ✅ Prevents disk exhaustion
- ✅ Prevents runaway training (7 day timeout)
- ✅ Detects OOM errors early
- ✅ Validates paths (no access outside allowed dirs)
- ✅ Checkpoint size limits prevent attacks

---

### 9. TensorBoard Integration: Visual Monitoring

**Decision**: Provide TensorBoard integration for visual progress monitoring.

**TensorBoard Launcher** (`infrastructure/piper/tensorboard_launcher.py`):
```python
import subprocess
from pathlib import Path
from typing import Optional

class TensorBoardLauncher:
    """Launches and manages TensorBoard for training monitoring."""
    
    def __init__(self, logdir: Path, port: int = 6006):
        """Initialize TensorBoard launcher.
        
        Args:
            logdir: Directory with TensorBoard logs
            port: Port to run TensorBoard server (default: 6006)
        """
        self.logdir = logdir
        self.port = port
        self.process: Optional[subprocess.Popen] = None
    
    def launch(self) -> None:
        """Launch TensorBoard in background process.
        
        Raises:
            RuntimeError: If TensorBoard already running
        """
        if self.process is not None:
            raise RuntimeError("TensorBoard already running")
        
        # Start TensorBoard
        self.process = subprocess.Popen(
            ["tensorboard", "--logdir", str(self.logdir), "--port", str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"TensorBoard started: http://localhost:{self.port}")
    
    def stop(self) -> None:
        """Stop TensorBoard process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
    
    def is_running(self) -> bool:
        """Check if TensorBoard is running.
        
        Returns:
            True if running
        """
        return self.process is not None and self.process.poll() is None
```

**Rationale**:
- ✅ Visual Monitoring: Loss curves, learning rate, spectrograms
- ✅ Non-Blocking: Runs in separate process
- ✅ Easy Access: Accessible via browser (http://localhost:6006)
- ✅ Standard Tool: Piper already generates TensorBoard logs

---

### 10. Error Handling Strategy: Graceful Recovery

**Decision**: Handle common training errors gracefully with recovery suggestions.

**Error Categories**:

1. **Out of Memory (OOM)**:
   - Detection: Parse CUDA OOM errors from stderr
   - Recovery: Suggest reducing batch_size
   - Automatic: Retry with batch_size // 2

2. **Checkpoint Corruption**:
   - Detection: Validate checkpoint after save
   - Recovery: Use previous checkpoint
   - Prevention: Save to temp file first, then rename

3. **Training Divergence** (loss → NaN):
   - Detection: Monitor loss in progress monitor
   - Recovery: Suggest lowering learning_rate
   - Automatic: Early stop if loss diverges

4. **Disk Full**:
   - Detection: Check disk space before checkpoint save
   - Recovery: Delete old checkpoints, suggest cleanup
   - Prevention: Monitor disk space continuously

5. **Process Crash**:
   - Detection: Monitor process exit code
   - Recovery: Resume from latest checkpoint
   - Logging: Capture stderr for debugging

**Error Handler** (`infrastructure/piper/error_handler.py`):
```python
import re
from pathlib import Path
from typing import Optional

class TrainingErrorHandler:
    """Handles common training errors with recovery suggestions."""
    
    OOM_PATTERNS = [
        re.compile(r"CUDA out of memory"),
        re.compile(r"RuntimeError.*out of memory"),
    ]
    
    @staticmethod
    def detect_error_type(stderr: str) -> str | None:
        """Detect error type from stderr output.
        
        Args:
            stderr: Standard error output from training process
            
        Returns:
            Error type string, or None if no known error
        """
        if any(pattern.search(stderr) for pattern in TrainingErrorHandler.OOM_PATTERNS):
            return "OUT_OF_MEMORY"
        
        if "NaN" in stderr or "inf" in stderr:
            return "LOSS_DIVERGENCE"
        
        if "No space left on device" in stderr:
            return "DISK_FULL"
        
        if "Killed" in stderr:
            return "PROCESS_KILLED"
        
        return None
    
    @staticmethod
    def suggest_recovery(error_type: str, config: TrainingConfig) -> str:
        """Suggest recovery action for error type.
        
        Args:
            error_type: Error type string
            config: Current training configuration
            
        Returns:
            Human-readable recovery suggestion
        """
        if error_type == "OUT_OF_MEMORY":
            new_batch_size = max(1, config.batch_size // 2)
            return (
                f"Out of memory error detected. Try reducing batch size:\n"
                f"  Current: {config.batch_size}\n"
                f"  Suggested: {new_batch_size}\n"
                f"  Command: --batch-size {new_batch_size}"
            )
        
        elif error_type == "LOSS_DIVERGENCE":
            new_lr = config.learning_rate / 10
            return (
                f"Loss divergence detected (NaN/inf). Try lowering learning rate:\n"
                f"  Current: {config.learning_rate}\n"
                f"  Suggested: {new_lr}\n"
                f"  Command: --learning-rate {new_lr}"
            )
        
        elif error_type == "DISK_FULL":
            return (
                f"Disk full error. Free up space:\n"
                f"  1. Delete old checkpoints: python scripts/cleanup_checkpoints.py\n"
                f"  2. Check disk usage: df -h\n"
                f"  3. Resume training after cleanup"
            )
        
        elif error_type == "PROCESS_KILLED":
            return (
                f"Training process killed (likely by OOM killer).\n"
                f"  1. Check system memory: free -h\n"
                f"  2. Reduce batch size: --batch-size {config.batch_size // 2}\n"
                f"  3. Close other applications to free memory"
            )
        
        return "Unknown error. Check logs for details."
```

**Rationale**:
- ✅ Actionable Guidance: Clear recovery steps
- ✅ Automatic Detection: Parses errors from logs
- ✅ Context-Aware: Suggests changes based on current config
- ✅ User-Friendly: Plain language explanations

---

## Implementation Plan

### Phase 5a: Domain Layer (TDD FIRST)

**Day 1: Value Objects**
1. Write tests for HardwareAccelerator, TrainingConfig
   - `tests/unit/test_training_value_objects.py`
   - Run tests → FAIL (not implemented)
2. Implement value objects
   - `piper_voice/core/value_objects.py` (add new classes)
   - Run tests → PASS

**Day 2: Entities**
1. Write tests for TrainingRun, TrainingMetrics, TrainingStatus
   - `tests/unit/test_training_entities.py`
   - Run tests → FAIL (not implemented)
2. Implement entities
   - `piper_voice/core/entities.py` (add TrainingRun)
   - Run tests → PASS

### Phase 5b: Infrastructure Layer (TDD FIRST)

**Day 3: Checkpoint Manager**
1. Write tests for CheckpointManager
   - `tests/unit/test_checkpoint_manager.py`
   - Run tests → FAIL (not implemented)
2. Implement CheckpointManager
   - `piper_voice/infrastructure/piper/checkpoint_manager.py`
   - Run tests → PASS

**Day 4: Hardware Detection**
1. Write tests for HardwareDetector
   - `tests/unit/test_hardware_detector.py`
   - Run tests → FAIL (not implemented)
2. Implement HardwareDetector
   - `piper_voice/infrastructure/piper/hardware_detector.py`
   - Run tests → PASS

**Day 5: Training Adapter**
1. Write tests for PiperTrainingAdapter
   - `tests/unit/test_training_adapter.py`
   - Run tests → FAIL (not implemented)
2. Implement PiperTrainingAdapter
   - `piper_voice/infrastructure/piper/training_adapter.py`
   - Run tests → PASS

**Day 6: Progress Monitor**
1. Write tests for ProgressMonitor
   - `tests/unit/test_progress_monitor.py`
   - Run tests → FAIL (not implemented)
2. Implement ProgressMonitor
   - `piper_voice/infrastructure/piper/progress_monitor.py`
   - Run tests → PASS

### Phase 5c: Application Layer (TDD FIRST)

**Day 7: Training Use Case**
1. Write integration tests
   - `tests/integration/test_train_japanese_voice.py`
   - Run tests → FAIL (not implemented)
2. Implement use case
   - `piper_voice/application/train_japanese_voice.py`
   - Run tests → PASS

### Phase 5d: CLI and Real Training

**Day 8: CLI Script**
1. Add CLI script
   - `scripts/train_voice.py`
2. Test with mock dataset (10 samples, 2 epochs)
3. Verify checkpoint creation and progress monitoring

**Day 9: Transfer Learning Test**
1. Download base checkpoint (e.g., French voice)
2. Run training with base checkpoint
3. Verify faster convergence (intelligible speech < 100 epochs)
4. Compare with training from scratch

**Day 10: Real JSUT Training**
1. Run full training on JSUT dataset (7,300 samples)
2. Monitor progress (TensorBoard)
3. Verify checkpoint saves
4. Test interruption and resumption
5. Generate training report

**Deliverables**:
- [ ] TrainingConfig, HardwareAccelerator value objects with tests (100% coverage)
- [ ] TrainingRun entity with tests (100% coverage)
- [ ] CheckpointManager with tests (95% coverage)
- [ ] HardwareDetector with tests (90% coverage)
- [ ] PiperTrainingAdapter with tests (90% coverage)
- [ ] ProgressMonitor with tests (85% coverage)
- [ ] train_japanese_voice use case with tests (90% coverage)
- [ ] CLI script (`scripts/train_voice.py`)
- [ ] Training report (epochs reached, losses, duration)
- [ ] Validation of checkpoint resumption

---

## Consequences

### Positive

✅ **Subprocess Isolation**: Training crashes don't crash application
✅ **Interruptible**: Can stop and resume training at any time
✅ **Progress Monitoring**: Real-time loss tracking without blocking
✅ **Checkpoint Safety**: Validation, size limits, corruption detection
✅ **Hardware Flexibility**: Auto-detects GPU/MPS/CPU
✅ **Transfer Learning**: Loads base checkpoints for faster training
✅ **DDD Compliance**: Clean architecture with clear boundaries
✅ **Error Recovery**: Graceful handling with actionable suggestions
✅ **TensorBoard Integration**: Visual monitoring out of the box

### Negative

❌ **Subprocess Communication**: Must parse logs for progress (not ideal)
❌ **PyTorch Dependency**: Requires PyTorch for checkpoint validation
❌ **Disk Space**: Checkpoints consume significant disk space (5-100 GB)
❌ **Complexity**: More code than simple training script

### Risks

1. **Piper CLI Changes**: Piper training CLI may change in future versions
   - **Mitigation**: Pin piper_train version, test compatibility

2. **Checkpoint Corruption**: Power loss during save may corrupt checkpoint
   - **Mitigation**: Atomic saves (write to temp, then rename), keep multiple checkpoints

3. **Training Divergence**: Loss may diverge (NaN) with bad hyperparameters
   - **Mitigation**: Validation, gradient clipping, error detection

4. **Disk Exhaustion**: Checkpoints may fill disk during long training
   - **Mitigation**: Disk space monitoring, automatic cleanup, size limits

5. **Out of Memory**: Large batch size may exceed GPU memory
   - **Mitigation**: Memory checks before training, error detection, retry with smaller batch

---

## Validation Criteria (From STORY-005)

This architecture must satisfy all STORY-005 acceptance criteria:

- [ ] Training starts without errors when prerequisites met
- [ ] System detects and uses GPU/MPS when available
- [ ] Base checkpoint loads successfully (transfer learning)
- [ ] Training configuration validated before starting
- [ ] Training loss decreases consistently over epochs
- [ ] Real-time progress displays epoch, losses, time
- [ ] Checkpoints saved at configured frequency
- [ ] TensorBoard displays loss curves in real-time
- [ ] Training can be stopped without corrupting checkpoints
- [ ] Training can resume from any saved checkpoint
- [ ] Resumed training continues from exact epoch
- [ ] Optimizer state preserved on resume
- [ ] Transfer learning produces intelligible speech < 100 epochs
- [ ] Validation loss computed alongside training loss
- [ ] Sample audio files generated at milestone epochs
- [ ] Training works on GPU, MPS, and CPU
- [ ] Invalid configuration values rejected with errors
- [ ] At least one checkpoint saved during training
- [ ] Training logs capture all important events
- [ ] Training summary report contains metrics

---

## References

- [STORY-005: Piper Training Integration](../stories/STORY-005-piper-training-integration.md)
- [ADR-001: Japanese Voice Architecture](ADR-001-japanese-voice-architecture.md)
- [ADR-004: Piper Preprocessing Integration](ADR-004-piper-preprocessing-integration.md)
- [Piper TRAINING.md](https://github.com/rhasspy/piper/blob/master/TRAINING.md)
- [PyTorch Lightning Documentation](https://lightning.ai/docs/pytorch/stable/)
- CLAUDE.md: Project rules and principles (TDD, DDD, security)

---

**This ADR is the architectural authority for Piper training integration.**
All code must follow these decisions. TDD is mandatory. DDD boundaries are non-negotiable. Security validation is required. Training must be interruptible, resumable, and monitored for progress.
