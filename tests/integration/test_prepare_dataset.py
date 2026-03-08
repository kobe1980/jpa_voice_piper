"""Integration tests for dataset preparation use case.

Following TDD: These tests are written BEFORE implementation.
Tests the complete pipeline: load corpus → validate audio → generate metadata.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from piper_voice.application.prepare_dataset import PrepareDatasetUseCase
from piper_voice.infrastructure.audio.processor import LibrosaAudioProcessor
from piper_voice.infrastructure.filesystem.safe_fs import SafeFileSystem


@pytest.fixture
def create_jsut_with_audio(tmp_path: Path):
    """Factory fixture to create JSUT corpus with real audio files."""

    def _create(num_files: int = 3, sample_rate: int = 22050) -> Path:
        """Create JSUT corpus with real audio files for integration testing.

        Args:
            num_files: Number of audio files to create
            sample_rate: Sample rate for audio files

        Returns:
            Path to JSUT root directory
        """
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_lines = []

        for i in range(num_files):
            audio_id = f"BASIC5000_{i:04d}"

            # Create real audio file (1 second sine wave)
            duration = 1.0
            num_samples = int(duration * sample_rate)
            t = np.linspace(0, duration, num_samples, endpoint=False)
            audio = 0.5 * np.sin(2 * np.pi * 440 * t)

            audio_file = subset_dir / f"{audio_id}.wav"
            sf.write(audio_file, audio, sample_rate)

            transcript_lines.append(f"{audio_id}:これはテストです{i}")

        transcript_file.write_text("\n".join(transcript_lines), encoding="utf-8")

        return jsut_root

    return _create


@pytest.fixture
def prepare_use_case(tmp_path: Path) -> PrepareDatasetUseCase:
    """Create PrepareDatasetUseCase with real adapters."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create required directories
    (project_root / "dataset").mkdir()
    (project_root / "training").mkdir()

    filesystem = SafeFileSystem(project_root)
    audio_processor = LibrosaAudioProcessor()

    return PrepareDatasetUseCase(filesystem, audio_processor)


class TestPrepareDatasetUseCase:
    """Integration tests for PrepareDatasetUseCase."""

    def test_prepare_dataset_creates_metadata_file(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that prepare_dataset creates metadata.csv."""
        jsut_root = create_jsut_with_audio(num_files=3)
        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(jsut_root, output_dir)

        assert result.success
        assert (output_dir / "metadata.csv").exists()

    def test_prepare_dataset_generates_correct_metadata_format(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that metadata.csv has correct LJSPEECH format."""
        jsut_root = create_jsut_with_audio(num_files=2)
        output_dir = tmp_path / "project" / "dataset"

        prepare_use_case.execute(jsut_root, output_dir)

        metadata_file = output_dir / "metadata.csv"
        lines = metadata_file.read_text(encoding="utf-8").strip().split("\n")

        assert len(lines) == 2
        assert lines[0].startswith("BASIC5000_0000|")
        assert lines[1].startswith("BASIC5000_0001|")
        assert "これはテストです" in lines[0]

    def test_prepare_dataset_normalizes_audio_files(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that audio files are normalized to output directory."""
        jsut_root = create_jsut_with_audio(num_files=2, sample_rate=48000)
        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(
            jsut_root, output_dir, target_sample_rate=22050, normalize_audio=True
        )

        assert result.success

        # Check normalized audio files exist
        wav_dir = output_dir / "wav"
        assert wav_dir.exists()
        assert (wav_dir / "BASIC5000_0000.wav").exists()
        assert (wav_dir / "BASIC5000_0001.wav").exists()

        # Verify sample rate
        info = sf.info(wav_dir / "BASIC5000_0000.wav")
        assert info.samplerate == 22050

    def test_prepare_dataset_skips_normalization_if_disabled(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that audio normalization can be skipped."""
        jsut_root = create_jsut_with_audio(num_files=2)
        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(
            jsut_root, output_dir, normalize_audio=False
        )

        assert result.success

        # wav/ directory should not be created
        wav_dir = output_dir / "wav"
        assert not wav_dir.exists()

    def test_prepare_dataset_validates_audio_quality(
        self, prepare_use_case: PrepareDatasetUseCase, tmp_path: Path
    ) -> None:
        """Test that audio quality validation rejects bad audio."""
        # Create JSUT corpus with clipping audio
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        # Create audio with clipping (amplitude = 1.0)
        audio = np.ones(22050)  # 1 second of maximum amplitude
        audio_file = subset_dir / "BASIC5000_0000.wav"
        sf.write(audio_file, audio, 22050)

        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_file.write_text("BASIC5000_0000:テスト", encoding="utf-8")

        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(
            jsut_root, output_dir, validate_quality=True
        )

        # Should fail due to clipping
        assert not result.success
        assert (
            "clipping" in result.message.lower()
            or "quality" in result.message.lower()
        )

    def test_prepare_dataset_skips_quality_validation_if_disabled(
        self, prepare_use_case: PrepareDatasetUseCase, tmp_path: Path
    ) -> None:
        """Test that quality validation can be disabled."""
        # Create JSUT corpus with clipping audio
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        audio = np.ones(22050)
        audio_file = subset_dir / "BASIC5000_0000.wav"
        sf.write(audio_file, audio, 22050)

        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_file.write_text("BASIC5000_0000:テスト", encoding="utf-8")

        output_dir = tmp_path / "project" / "dataset"

        # With validation disabled, should succeed even with bad audio
        result = prepare_use_case.execute(
            jsut_root, output_dir, validate_quality=False
        )

        assert result.success

    def test_prepare_dataset_returns_statistics(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that result includes dataset statistics."""
        jsut_root = create_jsut_with_audio(num_files=5)
        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(jsut_root, output_dir)

        assert result.success
        assert result.total_samples == 5
        assert result.failed_samples == 0

    def test_prepare_dataset_handles_partial_failures(
        self, prepare_use_case: PrepareDatasetUseCase, tmp_path: Path
    ) -> None:
        """Test that preparation continues when some files fail."""
        jsut_root = tmp_path / "jsut_ver1.1"
        jsut_root.mkdir()

        subset_dir = jsut_root / "basic5000" / "wav"
        subset_dir.mkdir(parents=True)

        # Create one good audio and one invalid file (not audio)
        good_audio = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 1, 22050))
        sf.write(subset_dir / "BASIC5000_0000.wav", good_audio, 22050)

        # Create invalid "audio" file (plain text)
        (subset_dir / "BASIC5000_0001.wav").write_text("not audio data")

        transcript_file = jsut_root / "basic5000" / "transcript_utf8.txt"
        transcript_file.write_text(
            "BASIC5000_0000:良いテスト\nBASIC5000_0001:悪いテスト", encoding="utf-8"
        )

        output_dir = tmp_path / "project" / "dataset"

        # Use normalization to trigger failure on invalid file
        result = prepare_use_case.execute(
            jsut_root, output_dir, normalize_audio=True, validate_quality=False
        )

        # Should succeed partially: good audio normalized, invalid skipped
        assert result.success  # At least one file succeeded
        assert result.total_samples == 2
        assert result.failed_samples == 1

        # Metadata should only include good file
        metadata_file = output_dir / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")
        assert "BASIC5000_0000" in content
        assert "BASIC5000_0001" not in content

    def test_prepare_dataset_raises_on_nonexistent_jsut_directory(
        self, prepare_use_case: PrepareDatasetUseCase, tmp_path: Path
    ) -> None:
        """Test that nonexistent JSUT directory raises error."""
        nonexistent = tmp_path / "nonexistent"
        output_dir = tmp_path / "project" / "dataset"

        result = prepare_use_case.execute(nonexistent, output_dir)

        assert not result.success
        assert "not found" in result.message.lower()

    def test_prepare_dataset_raises_on_invalid_output_directory(
        self,
        prepare_use_case: PrepareDatasetUseCase,
        create_jsut_with_audio,
        tmp_path: Path,
    ) -> None:
        """Test that invalid output directory raises error."""
        jsut_root = create_jsut_with_audio(num_files=2)
        forbidden_dir = Path("/etc/forbidden")

        result = prepare_use_case.execute(jsut_root, forbidden_dir)

        assert not result.success
        assert (
            "not allowed" in result.message.lower()
            or "permission" in result.message.lower()
        )
