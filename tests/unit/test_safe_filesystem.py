"""Unit tests for SafeFileSystem.

Following TDD: These tests are written BEFORE implementation.
Tests the security guardrails for filesystem operations.
"""

from pathlib import Path

import pytest

from piper_voice.infrastructure.filesystem.safe_fs import SafeFileSystem


class TestSafeFileSystem:
    """Tests for SafeFileSystem security guardrails."""

    def test_allowed_path_dataset(self) -> None:
        """Test that dataset/ paths are allowed."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_path_allowed(Path("/project/dataset/raw/audio.wav"))
        assert fs.is_path_allowed(Path("/project/dataset/wav/normalized.wav"))

    def test_allowed_path_training(self) -> None:
        """Test that training/ paths are allowed."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_path_allowed(Path("/project/training/config.json"))
        assert fs.is_path_allowed(Path("/project/training/dataset.jsonl"))

    def test_allowed_path_models(self) -> None:
        """Test that models/ paths are allowed."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_path_allowed(Path("/project/models/voice.onnx"))

    def test_allowed_path_logs(self) -> None:
        """Test that logs/ paths are allowed."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_path_allowed(Path("/project/logs/training.log"))

    def test_allowed_path_checkpoints(self) -> None:
        """Test that checkpoints/ paths are allowed."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_path_allowed(Path("/project/checkpoints/epoch_10.ckpt"))

    def test_reject_home_directory(self) -> None:
        """Test that $HOME paths are rejected."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert not fs.is_path_allowed(Path.home() / "file.txt")
        assert not fs.is_path_allowed(Path("/Users/user/file.txt"))

    def test_reject_root_directory(self) -> None:
        """Test that root / paths are rejected."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert not fs.is_path_allowed(Path("/etc/passwd"))
        assert not fs.is_path_allowed(Path("/tmp/file.txt"))

    def test_reject_ssh_keys(self) -> None:
        """Test that SSH key paths are rejected."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert not fs.is_path_allowed(Path.home() / ".ssh" / "id_rsa")

    def test_reject_outside_project_root(self) -> None:
        """Test that paths outside project root are rejected."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert not fs.is_path_allowed(Path("/other_project/file.txt"))
        assert not fs.is_path_allowed(Path("/project/../outside/file.txt"))

    def test_dataset_raw_is_readonly(self) -> None:
        """Test that dataset/raw/ is marked as read-only."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert fs.is_readonly_path(Path("/project/dataset/raw/audio.wav"))
        assert fs.is_readonly_path(Path("/project/dataset/raw/subdir/audio.wav"))

    def test_dataset_wav_is_not_readonly(self) -> None:
        """Test that dataset/wav/ is writable."""
        fs = SafeFileSystem(project_root=Path("/project"))

        assert not fs.is_readonly_path(Path("/project/dataset/wav/audio.wav"))

    def test_ensure_directory_creates_if_allowed(self, tmp_path: Path) -> None:
        """Test creating directory in allowed location."""
        fs = SafeFileSystem(project_root=tmp_path)

        new_dir = tmp_path / "dataset" / "test"
        fs.ensure_directory(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_rejects_forbidden_path(self) -> None:
        """Test that creating directory in forbidden location raises error."""
        fs = SafeFileSystem(project_root=Path("/project"))

        with pytest.raises(PermissionError, match="not allowed"):
            fs.ensure_directory(Path("/etc/newdir"))

    def test_list_audio_files_finds_wav(self, tmp_path: Path) -> None:
        """Test listing WAV files in directory."""
        fs = SafeFileSystem(project_root=tmp_path)

        # Create test directory with audio files
        audio_dir = tmp_path / "dataset" / "raw"
        audio_dir.mkdir(parents=True)

        (audio_dir / "file1.wav").touch()
        (audio_dir / "file2.wav").touch()
        (audio_dir / "readme.txt").touch()

        audio_files = fs.list_audio_files(audio_dir)

        assert len(audio_files) == 2
        assert all(f.suffix == ".wav" for f in audio_files)
        assert audio_dir / "file1.wav" in audio_files
        assert audio_dir / "file2.wav" in audio_files

    def test_list_audio_files_rejects_forbidden_path(self) -> None:
        """Test that listing files in forbidden location raises error."""
        fs = SafeFileSystem(project_root=Path("/project"))

        with pytest.raises(PermissionError, match="not allowed"):
            fs.list_audio_files(Path("/etc"))

    def test_list_audio_files_raises_if_not_exists(self, tmp_path: Path) -> None:
        """Test that listing non-existent directory raises error."""
        fs = SafeFileSystem(project_root=tmp_path)

        with pytest.raises(FileNotFoundError):
            fs.list_audio_files(tmp_path / "nonexistent")

    def test_reject_write_to_readonly_path(self) -> None:
        """Test that attempting to write to read-only path raises error."""
        fs = SafeFileSystem(project_root=Path("/project"))

        readonly_path = Path("/project/dataset/raw/file.wav")

        with pytest.raises(PermissionError, match="read-only"):
            fs.check_writable(readonly_path)

    def test_allow_write_to_writable_path(self, tmp_path: Path) -> None:
        """Test that writing to writable path is allowed."""
        fs = SafeFileSystem(project_root=tmp_path)

        writable_path = tmp_path / "dataset" / "wav" / "file.wav"

        # Should not raise
        fs.check_writable(writable_path)

    def test_normalize_path_resolves_relative(self) -> None:
        """Test that relative paths are resolved to absolute."""
        fs = SafeFileSystem(project_root=Path("/project"))

        relative_path = Path("dataset/raw/audio.wav")
        normalized = fs.normalize_path(relative_path)

        assert normalized.is_absolute()
        assert "dataset/raw/audio.wav" in str(normalized)

    def test_normalize_path_resolves_parent_references(self) -> None:
        """Test that .. references are resolved."""
        fs = SafeFileSystem(project_root=Path("/project"))

        path_with_parent = Path("/project/dataset/../dataset/raw/audio.wav")
        normalized = fs.normalize_path(path_with_parent)

        assert ".." not in str(normalized)
        assert normalized == Path("/project/dataset/raw/audio.wav")
