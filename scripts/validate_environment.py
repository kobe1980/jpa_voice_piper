#!/usr/bin/env python3
"""
Environment validation script for Piper TTS training.
Run this BEFORE starting training to catch issues early.

Usage:
    python scripts/validate_environment.py
"""

import json
import platform
import subprocess
import sys
from pathlib import Path


def print_header(text: str) -> None:
    """Print section header."""
    print()
    print("=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_check(name: str, status: bool, details: str = "") -> None:
    """Print check result."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if details:
        print(f"   {details}")


def check_python_version() -> bool:
    """Check Python version is 3.11+."""
    version = sys.version_info
    is_ok = version >= (3, 11)
    details = f"Python {version.major}.{version.minor}.{version.micro}"
    print_check("Python version >= 3.11", is_ok, details)
    return is_ok


def check_pytorch() -> tuple[bool, str]:
    """Check PyTorch is installed and working."""
    try:
        import torch

        version = torch.__version__
        print_check("PyTorch installed", True, f"Version: {version}")
        return True, version
    except ImportError:
        print_check("PyTorch installed", False, "NOT INSTALLED")
        return False, ""


def check_cuda() -> tuple[bool, str]:
    """Check CUDA availability."""
    try:
        import torch

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            device_count = torch.cuda.device_count()
            cuda_version = torch.version.cuda
            print_check(
                "CUDA available",
                True,
                f"{device_count}x {device_name}, CUDA {cuda_version}",
            )
            return True, device_name
        else:
            print_check("CUDA available", False, "No CUDA GPU detected")
            return False, ""
    except Exception as e:
        print_check("CUDA available", False, f"Error: {e}")
        return False, ""


def check_mps() -> bool:
    """Check Apple Silicon MPS availability."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False

    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print_check("MPS (Apple Silicon)", True, "Available")
            return True
        else:
            print_check("MPS (Apple Silicon)", False, "Not available")
            return False
    except Exception as e:
        print_check("MPS (Apple Silicon)", False, f"Error: {e}")
        return False


def check_piper_installation() -> bool:
    """Check Piper training module is installed."""
    try:
        import piper.train

        print_check("Piper training installed", True)
        return True
    except ImportError:
        print_check(
            "Piper training installed",
            False,
            "Run: pip install piper-tts[training]",
        )
        return False


def check_dataset_files(project_root: Path) -> tuple[bool, int]:
    """Check dataset files exist and count samples."""
    dataset_csv = project_root / "dataset" / "prepared" / "metadata_phonemes.csv"
    audio_dir = project_root / "dataset" / "prepared" / "wav"
    phoneme_map = project_root / "dataset" / "prepared" / "phoneme_map.json"

    all_ok = True
    sample_count = 0

    # Check CSV
    if dataset_csv.exists():
        sample_count = sum(1 for _ in dataset_csv.open())
        print_check("Dataset CSV exists", True, f"{sample_count} samples")
    else:
        print_check("Dataset CSV exists", False, str(dataset_csv))
        all_ok = False

    # Check audio directory
    if audio_dir.exists():
        audio_count = len(list(audio_dir.glob("*.wav")))
        print_check("Audio directory exists", True, f"{audio_count} WAV files")
    else:
        print_check("Audio directory exists", False, str(audio_dir))
        all_ok = False

    # Check phoneme map
    if phoneme_map.exists():
        with phoneme_map.open() as f:
            data = json.load(f)
            phoneme_count = len(data.get("phonemes", {}))
        print_check("Phoneme map exists", True, f"{phoneme_count} phonemes")
    else:
        print_check("Phoneme map exists", False, str(phoneme_map))
        all_ok = False

    return all_ok, sample_count


def check_disk_space(project_root: Path) -> bool:
    """Check available disk space."""
    import shutil

    stat = shutil.disk_usage(project_root)
    free_gb = stat.free / (1024**3)
    is_ok = free_gb > 10  # Need at least 10GB free

    print_check(
        "Disk space available",
        is_ok,
        f"{free_gb:.1f} GB free (need > 10 GB)",
    )
    return is_ok


def check_optional_dependencies() -> None:
    """Check optional but recommended dependencies."""
    print()
    print("Optional dependencies:")

    # TensorBoard
    try:
        import tensorboard

        print_check("TensorBoard", True, "Installed")
    except ImportError:
        print_check(
            "TensorBoard",
            False,
            "Not installed (recommended: pip install tensorboard)",
        )

    # soundfile
    try:
        import soundfile

        print_check("soundfile", True, "Installed")
    except ImportError:
        print_check(
            "soundfile",
            False,
            "Not installed (recommended: pip install soundfile)",
        )

    # librosa
    try:
        import librosa

        print_check("librosa", True, "Installed")
    except ImportError:
        print_check(
            "librosa",
            False,
            "Not installed (recommended: pip install librosa)",
        )


def main() -> int:
    """Main entry point."""
    print_header("Environment Validation for Piper TTS Training")

    project_root = Path(__file__).parent.parent
    print(f"\nProject root: {project_root}")

    issues = []

    # Check Python
    print_header("Python Environment")
    if not check_python_version():
        issues.append("Python version too old (need 3.11+)")

    # Check PyTorch
    print_header("PyTorch")
    pytorch_ok, pytorch_version = check_pytorch()
    if not pytorch_ok:
        issues.append("PyTorch not installed")

    # Check accelerators
    print_header("Hardware Accelerators")
    cuda_ok, gpu_name = check_cuda()
    mps_ok = check_mps()

    if not cuda_ok and not mps_ok:
        print()
        print("⚠️  WARNING: No GPU detected!")
        print("   Training will be VERY SLOW on CPU (days to weeks)")
        print()
        print("   Recommendations:")
        if platform.system() == "Windows":
            print("   - Install NVIDIA drivers + CUDA Toolkit")
            print("   - Reinstall PyTorch with CUDA support:")
            print("     pip install torch --index-url https://download.pytorch.org/whl/cu118")
        elif platform.system() == "Darwin":
            if platform.machine() == "arm64":
                print("   - You have Apple Silicon but MPS is not available")
                print("   - Upgrade to macOS 12.3+ and PyTorch 1.12+")
            else:
                print("   - Consider using cloud GPU (Google Colab, AWS, etc.)")
        else:
            print("   - Install NVIDIA drivers + CUDA")
            print("   - Use cloud GPU instance")

    # Check Piper
    print_header("Piper TTS")
    if not check_piper_installation():
        issues.append("Piper training module not installed")

    # Check dataset
    print_header("Dataset")
    dataset_ok, sample_count = check_dataset_files(project_root)
    if not dataset_ok:
        issues.append("Dataset files missing or incomplete")
    elif sample_count < 100:
        print()
        print("⚠️  WARNING: Dataset has only", sample_count, "samples")
        print("   Recommended: > 1000 samples for good quality")

    # Check disk space
    print_header("System Resources")
    if not check_disk_space(project_root):
        issues.append("Insufficient disk space (need > 10 GB)")

    # Check optional deps
    check_optional_dependencies()

    # Final summary
    print_header("Validation Summary")

    if not issues:
        print()
        print("✅ All critical checks passed!")
        print()
        print("You can start training with:")
        print("  python scripts/train_japanese_voice.py")
        print()

        # Recommend accelerator
        if cuda_ok:
            print(f"Detected GPU: {gpu_name}")
            print("Estimated training time: 6-12 hours (transfer learning)")
        elif mps_ok:
            print("Detected: Apple Silicon MPS")
            print("Estimated training time: 12-24 hours (transfer learning)")
        else:
            print("No GPU detected - training on CPU")
            print("Estimated training time: 3-7 days (transfer learning)")

        return 0
    else:
        print()
        print("❌ Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        print("Please fix these issues before starting training.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
