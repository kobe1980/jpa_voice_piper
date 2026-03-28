#!/usr/bin/env python3
"""
Training script for Japanese voice (Piper TTS)
Cross-platform: Windows, Linux, macOS

Usage:
    python scripts/train_japanese_voice.py [--accelerator gpu|mps|cpu] [--from-scratch]

Requirements:
    - Dataset prepared in dataset/prepared/
    - piper-training installed (pip install piper-tts[training])
    - For transfer learning: French checkpoint downloaded
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve


def detect_accelerator() -> str:
    """Auto-detect available hardware accelerator."""
    print("🔍 Auto-detecting hardware accelerator...")

    # Check for NVIDIA GPU (CUDA)
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            print("✅ Detected NVIDIA GPU (CUDA)")
            return "gpu"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check for Apple Silicon (MPS)
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        print("✅ Detected Apple Silicon (MPS)")
        return "mps"

    # Fallback to CPU
    print("⚠️  No GPU detected, using CPU (slow!)")
    return "cpu"


def validate_dataset(dataset_csv: Path, audio_dir: Path) -> int:
    """Validate dataset files exist and return sample count."""
    print()
    print("=" * 80)
    print("🔍 Validating dataset")
    print("=" * 80)

    if not dataset_csv.exists():
        print(f"❌ ERROR: Dataset CSV not found: {dataset_csv}")
        print()
        print("Please prepare the dataset first:")
        print("  python scripts/prepare_jsut_dataset.py \\")
        print("    --jsut-dir dataset/jsut/basic5000 \\")
        print("    --output-dir dataset/prepared \\")
        print("    --sample-rate 22050")
        print()
        print("Then phonemize:")
        print("  python scripts/phonemize_japanese.py \\")
        print("    --input dataset/prepared/metadata.csv \\")
        print("    --output dataset/prepared/metadata_phonemes.csv \\")
        print("    --phoneme-map dataset/prepared/phoneme_map.json")
        sys.exit(1)

    if not audio_dir.exists():
        print(f"❌ ERROR: Audio directory not found: {audio_dir}")
        sys.exit(1)

    sample_count = sum(1 for _ in dataset_csv.open())
    print(f"✅ Dataset validated: {sample_count} samples")

    if sample_count < 100:
        print(f"⚠️  WARNING: Dataset has only {sample_count} samples (recommend > 1000)")

    return sample_count


def download_checkpoint(checkpoint_url: str, checkpoint_file: Path) -> None:
    """Download transfer learning checkpoint if not exists."""
    print()
    print("=" * 80)
    print("📥 Transfer Learning Setup")
    print("=" * 80)

    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    if checkpoint_file.exists():
        print(f"✅ Checkpoint already downloaded: {checkpoint_file}")
    else:
        print("📥 Downloading French checkpoint for transfer learning...")
        print(f"URL: {checkpoint_url}")

        def report_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            print(f"\rDownloading: {percent:.1f}%", end="", flush=True)

        try:
            urlretrieve(checkpoint_url, checkpoint_file, reporthook=report_hook)
            print()
            print("✅ Checkpoint downloaded")
        except Exception as e:
            print()
            print(f"❌ ERROR: Download failed: {e}")
            print()
            print("Please download manually:")
            print(f"  {checkpoint_url}")
            print(f"Save to: {checkpoint_file}")
            sys.exit(1)

    size_mb = checkpoint_file.stat().st_size / (1024 * 1024)
    print(f"Checkpoint size: {size_mb:.1f} MB")


def print_training_config(
    accelerator: str,
    num_workers: int,
    dataset_csv: Path,
    audio_dir: Path,
    sample_count: int,
    sample_rate: int,
    phoneme_type: str,
    batch_size: int,
    learning_rate: float,
    max_epochs: int,
    validation_split: float,
    from_scratch: bool,
    checkpoint_file: Path | None,
) -> None:
    """Print training configuration summary."""
    print()
    print("=" * 80)
    print("🚀 Training Configuration")
    print("=" * 80)
    print("Hardware:")
    print(f"  Accelerator:        {accelerator}")
    print(f"  Dataloader workers: {num_workers}")
    print()
    print("Dataset:")
    print(f"  CSV file:           {dataset_csv}")
    print(f"  Audio directory:    {audio_dir}")
    print(f"  Sample count:       {sample_count}")
    print(f"  Sample rate:        {sample_rate} Hz")
    print(f"  Phoneme type:       {phoneme_type} (hiragana-as-phonemes)")
    print()
    print("Hyperparameters:")
    print(f"  Batch size:         {batch_size}")
    print(f"  Learning rate:      {learning_rate}")
    print(f"  Max epochs:         {max_epochs}")
    print(f"  Validation split:   {validation_split}")
    print()
    print("Transfer learning:")
    if not from_scratch:
        print("  Enabled:            YES")
        print(f"  Checkpoint:         {checkpoint_file}")
    else:
        print("  Enabled:            NO (training from scratch)")
    print("=" * 80)
    print()


def estimate_training_time(accelerator: str, from_scratch: bool) -> None:
    """Print estimated training time."""
    print("⏰ Estimated training time:")
    if not from_scratch:
        times = {
            "gpu": "6-12 hours",
            "mps": "12-24 hours",
            "cpu": "3-7 days (!)",
        }
    else:
        times = {
            "gpu": "24-48 hours",
            "mps": "48-96 hours",
            "cpu": "7-14 days (!)",
        }

    time_str = times.get(accelerator, "Unknown")
    if accelerator == "gpu":
        print(f"   GPU (CUDA):   {time_str}")
    elif accelerator == "mps":
        print(f"   Apple Silicon: {time_str}")
    elif accelerator == "cpu":
        print(f"   CPU:          {time_str}")

    print()


def build_train_command(
    voice_name: str,
    dataset_csv: Path,
    audio_dir: Path,
    cache_dir: Path,
    config_path: Path,
    batch_size: int,
    validation_split: float,
    num_workers: int,
    phoneme_type: str,
    sample_rate: int,
    learning_rate: float,
    max_epochs: int,
    check_val_every_n_epoch: int,
    accelerator: str,
    checkpoint_file: Path | None = None,
) -> list[str]:
    """Build training command as list of arguments."""
    cmd = [
        sys.executable,
        "-m",
        "piper.train",
        "fit",
        "--data.voice_name",
        voice_name,
        "--data.csv_path",
        str(dataset_csv),
        "--data.audio_dir",
        str(audio_dir),
        "--data.cache_dir",
        str(cache_dir),
        "--data.config_path",
        str(config_path),
        "--data.batch_size",
        str(batch_size),
        "--data.validation_split",
        str(validation_split),
        "--data.num_workers",
        str(num_workers),
        "--data.phoneme_type",
        phoneme_type,
        "--data.espeak_voice",
        "ja",
        "--model.sample_rate",
        str(sample_rate),
        "--model.learning_rate",
        str(learning_rate),
        "--trainer.max_epochs",
        str(max_epochs),
        "--trainer.check_val_every_n_epoch",
        str(check_val_every_n_epoch),
        "--trainer.accelerator",
        accelerator,
        "--trainer.precision",
        "32",
    ]

    if checkpoint_file is not None:
        cmd.extend(["--ckpt_path", str(checkpoint_file)])

    return cmd


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train Japanese voice model for Piper TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect GPU/MPS/CPU
  python scripts/train_japanese_voice.py

  # Force CUDA GPU
  python scripts/train_japanese_voice.py --accelerator gpu

  # Force Apple Silicon MPS
  python scripts/train_japanese_voice.py --accelerator mps

  # Train from scratch (no transfer learning)
  python scripts/train_japanese_voice.py --from-scratch
        """,
    )

    parser.add_argument(
        "--accelerator",
        choices=["gpu", "mps", "cpu", "auto"],
        default="auto",
        help="Hardware accelerator (default: auto-detect)",
    )
    parser.add_argument(
        "--from-scratch",
        action="store_true",
        help="Train from scratch (no transfer learning)",
    )

    args = parser.parse_args()

    # ========================================================================
    # Configuration
    # ========================================================================

    project_root = Path(__file__).parent.parent
    dataset_csv = project_root / "dataset" / "prepared" / "metadata_phonemes.csv"
    audio_dir = project_root / "dataset" / "prepared" / "wav"
    cache_dir = project_root / "training"
    config_path = cache_dir / "config.json"

    voice_name = "ja_JP-jsut-medium"
    sample_rate = 22050
    phoneme_type = "text"

    # Hyperparameters
    batch_size = 32
    learning_rate = 0.00005 if not args.from_scratch else 0.0001
    max_epochs = 200 if not args.from_scratch else 500
    validation_split = 0.1
    check_val_every_n_epoch = 5

    # Transfer learning
    checkpoint_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt"
    checkpoint_file = project_root / "checkpoints" / "fr_FR-siwis-medium.ckpt"

    # ========================================================================
    # Auto-detect accelerator
    # ========================================================================

    accelerator = args.accelerator
    if accelerator == "auto":
        accelerator = detect_accelerator()

    # Platform-specific configuration
    num_workers = 0 if accelerator == "mps" else 4

    if accelerator == "mps":
        print("🍎 Apple Silicon detected: disabling dataloader workers")

    if accelerator == "cpu":
        print("⚠️  WARNING: CPU training is VERY SLOW (days to weeks)")
        print("Consider using a GPU instance (AWS, Google Colab, etc.)")

    # ========================================================================
    # Validate dataset
    # ========================================================================

    sample_count = validate_dataset(dataset_csv, audio_dir)

    # ========================================================================
    # Download checkpoint (if needed)
    # ========================================================================

    checkpoint_for_training = None
    if not args.from_scratch:
        download_checkpoint(checkpoint_url, checkpoint_file)
        checkpoint_for_training = checkpoint_file
    else:
        print()
        print("=" * 80)
        print("🏗️  Training from Scratch")
        print("=" * 80)
        print("⚠️  WARNING: Training from scratch will take MUCH longer")

    # ========================================================================
    # Print configuration and confirm
    # ========================================================================

    print_training_config(
        accelerator=accelerator,
        num_workers=num_workers,
        dataset_csv=dataset_csv,
        audio_dir=audio_dir,
        sample_count=sample_count,
        sample_rate=sample_rate,
        phoneme_type=phoneme_type,
        batch_size=batch_size,
        learning_rate=learning_rate,
        max_epochs=max_epochs,
        validation_split=validation_split,
        from_scratch=args.from_scratch,
        checkpoint_file=checkpoint_for_training,
    )

    estimate_training_time(accelerator, args.from_scratch)

    try:
        input("Press ENTER to start training, or Ctrl+C to cancel...")
    except KeyboardInterrupt:
        print("\n❌ Training cancelled")
        return 1

    # ========================================================================
    # Build and execute training command
    # ========================================================================

    train_cmd = build_train_command(
        voice_name=voice_name,
        dataset_csv=dataset_csv,
        audio_dir=audio_dir,
        cache_dir=cache_dir,
        config_path=config_path,
        batch_size=batch_size,
        validation_split=validation_split,
        num_workers=num_workers,
        phoneme_type=phoneme_type,
        sample_rate=sample_rate,
        learning_rate=learning_rate,
        max_epochs=max_epochs,
        check_val_every_n_epoch=check_val_every_n_epoch,
        accelerator=accelerator,
        checkpoint_file=checkpoint_for_training,
    )

    print()
    print("=" * 80)
    print("🚀 Starting Training")
    print("=" * 80)
    print()
    print("Command:")
    print(" ".join(train_cmd))
    print()
    print("📊 Monitor progress:")
    print("  tensorboard --logdir ./lightning_logs --port 6006")
    print()
    print("=" * 80)
    print()

    # Execute training
    try:
        result = subprocess.run(train_cmd, check=False)
        exit_code = result.returncode
    except KeyboardInterrupt:
        print("\n❌ Training interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        return 1

    # ========================================================================
    # Post-training report
    # ========================================================================

    print()
    print("=" * 80)

    if exit_code == 0:
        print("✅ Training completed successfully!")
        print("=" * 80)
        print()
        print("Next steps:")
        print()
        print("1. Find best checkpoint:")
        print("   ls lightning_logs/version_*/checkpoints/*.ckpt")
        print()
        print("2. Export to ONNX:")
        print("   python -m piper.train.export_onnx \\")
        print("     lightning_logs/version_X/checkpoints/epoch=Y-step=Z.ckpt \\")
        print("     models/ja_JP-jsut-medium.onnx")
        print()
        print("3. Test synthesis:")
        print("   echo 'こんにちは' | piper -m models/ja_JP-jsut-medium.onnx")
        print()
    else:
        print(f"❌ Training failed with exit code: {exit_code}")
        print("=" * 80)
        print()
        print("Check logs:")
        print("  tensorboard --logdir ./lightning_logs")
        print()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
