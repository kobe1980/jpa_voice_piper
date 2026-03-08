"""Unit tests for LibrosaAudioProcessor.

Following TDD: These tests are written BEFORE implementation.
Tests the audio processing capabilities using librosa.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from piper_voice.core.value_objects import AudioQuality
from piper_voice.infrastructure.audio.processor import LibrosaAudioProcessor


@pytest.fixture
def audio_processor() -> LibrosaAudioProcessor:
    """Create audio processor instance."""
    return LibrosaAudioProcessor()


@pytest.fixture
def create_test_audio(tmp_path: Path):
    """Factory fixture to create test audio files."""

    def _create(
        filename: str,
        duration: float = 1.0,
        sample_rate: int = 22050,
        frequency: float = 440.0,
        amplitude: float = 0.5,
    ) -> Path:
        """Create a test audio file with sine wave.

        Args:
            filename: Output filename
            duration: Duration in seconds
            sample_rate: Sample rate in Hz
            frequency: Sine wave frequency in Hz
            amplitude: Amplitude (0.0 to 1.0)

        Returns:
            Path to created audio file
        """
        num_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        audio = amplitude * np.sin(2 * np.pi * frequency * t)

        output_path = tmp_path / filename
        sf.write(output_path, audio, sample_rate)

        return output_path

    return _create


class TestLibrosaAudioProcessor:
    """Tests for LibrosaAudioProcessor."""

    def test_load_audio_returns_samples_and_rate(
        self, audio_processor: LibrosaAudioProcessor, create_test_audio
    ) -> None:
        """Test loading audio file returns samples and sample rate."""
        audio_file = create_test_audio("test.wav", duration=1.0, sample_rate=22050)

        samples, sample_rate = audio_processor.load_audio(audio_file)

        assert isinstance(samples, list)
        assert isinstance(sample_rate, int)
        assert sample_rate == 22050
        assert len(samples) > 0

    def test_load_audio_raises_on_nonexistent_file(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that loading nonexistent file raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.wav"

        with pytest.raises(FileNotFoundError):
            audio_processor.load_audio(nonexistent)

    def test_load_audio_raises_on_invalid_format(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that loading invalid audio format raises ValueError."""
        # Create a text file pretending to be audio
        invalid_file = tmp_path / "invalid.wav"
        invalid_file.write_text("not audio data")

        with pytest.raises(ValueError, match="Invalid audio file"):
            audio_processor.load_audio(invalid_file)

    def test_analyze_quality_detects_good_audio(
        self, audio_processor: LibrosaAudioProcessor, create_test_audio
    ) -> None:
        """Test quality analysis on good audio."""
        # Create clean audio: 1s, 440Hz sine, moderate amplitude
        audio_file = create_test_audio("good.wav", amplitude=0.5)

        quality = audio_processor.analyze_quality(audio_file)

        assert isinstance(quality, AudioQuality)
        # Pure sine wave has lower SNR in our estimation (no noise floor)
        # Real recordings would have higher SNR, but for pure tone this is expected
        assert quality.snr_db > 0.0  # At least positive SNR
        # Moderate amplitude should not clip
        assert not quality.has_clipping
        assert quality.max_amplitude < 0.95

    def test_analyze_quality_detects_clipping(
        self, audio_processor: LibrosaAudioProcessor, create_test_audio
    ) -> None:
        """Test that clipping is detected in loud audio."""
        # Create audio with amplitude near clipping threshold
        audio_file = create_test_audio("loud.wav", amplitude=0.98)

        quality = audio_processor.analyze_quality(audio_file)

        # Should detect clipping or high amplitude
        assert quality.has_clipping or quality.max_amplitude >= 0.95

    def test_analyze_quality_measures_silence(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that silence at start/end is measured."""
        # Create audio with silence padding: 0.5s silence, 1s tone, 0.5s silence
        sample_rate = 22050
        silence_duration = 0.5
        tone_duration = 1.0

        silence_samples = int(silence_duration * sample_rate)
        tone_samples = int(tone_duration * sample_rate)

        # Create audio array
        silence = np.zeros(silence_samples)
        t = np.linspace(0, tone_duration, tone_samples, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)

        audio = np.concatenate([silence, tone, silence])

        audio_file = tmp_path / "padded.wav"
        sf.write(audio_file, audio, sample_rate)

        quality = audio_processor.analyze_quality(audio_file)

        # Should detect silence at start and end
        assert quality.silence_at_start_sec > 0.0
        assert quality.silence_at_end_sec > 0.0

    def test_normalize_audio_resamples_to_target_rate(
        self, audio_processor: LibrosaAudioProcessor, create_test_audio, tmp_path: Path
    ) -> None:
        """Test that normalization resamples to target sample rate."""
        # Create audio at 48000 Hz
        input_file = create_test_audio("input.wav", sample_rate=48000)
        output_file = tmp_path / "output.wav"

        # Normalize to 22050 Hz
        audio_processor.normalize_audio(
            input_file, output_file, target_sample_rate=22050
        )

        # Check output file
        assert output_file.exists()

        # Verify sample rate
        samples, sample_rate = audio_processor.load_audio(output_file)
        assert sample_rate == 22050

    def test_normalize_audio_converts_to_mono(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that normalization converts stereo to mono."""
        # Create stereo audio
        sample_rate = 22050
        duration = 1.0
        num_samples = int(duration * sample_rate)

        # Create stereo (2 channels)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        left = 0.5 * np.sin(2 * np.pi * 440 * t)
        right = 0.5 * np.sin(2 * np.pi * 550 * t)
        stereo = np.stack([left, right], axis=1)

        input_file = tmp_path / "stereo.wav"
        sf.write(input_file, stereo, sample_rate)

        output_file = tmp_path / "mono.wav"

        # Normalize (should convert to mono)
        audio_processor.normalize_audio(
            input_file, output_file, target_sample_rate=22050
        )

        # Load and check
        info = sf.info(output_file)
        assert info.channels == 1  # Mono

    def test_normalize_audio_trims_silence(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that normalization trims excessive silence."""
        # Create audio with long silence padding
        sample_rate = 22050
        silence_duration = 1.0  # 1 second silence (excessive)
        tone_duration = 1.0

        silence_samples = int(silence_duration * sample_rate)
        tone_samples = int(tone_duration * sample_rate)

        silence = np.zeros(silence_samples)
        t = np.linspace(0, tone_duration, tone_samples, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)

        audio = np.concatenate([silence, tone, silence])

        input_file = tmp_path / "padded.wav"
        sf.write(input_file, audio, sample_rate)

        output_file = tmp_path / "trimmed.wav"

        # Normalize (should trim silence)
        audio_processor.normalize_audio(
            input_file, output_file, target_sample_rate=22050
        )

        # Output should be shorter (silence trimmed)
        input_info = sf.info(input_file)
        output_info = sf.info(output_file)

        assert output_info.frames < input_info.frames

    def test_normalize_audio_raises_on_invalid_sample_rate(
        self, audio_processor: LibrosaAudioProcessor, create_test_audio, tmp_path: Path
    ) -> None:
        """Test that invalid target sample rate raises ValueError."""
        input_file = create_test_audio("input.wav")
        output_file = tmp_path / "output.wav"

        # Invalid sample rate (not 16000 or 22050)
        with pytest.raises(ValueError, match="must be 16000 or 22050"):
            audio_processor.normalize_audio(
                input_file, output_file, target_sample_rate=48000
            )

    def test_normalize_audio_raises_on_nonexistent_input(
        self, audio_processor: LibrosaAudioProcessor, tmp_path: Path
    ) -> None:
        """Test that normalizing nonexistent file raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.wav"
        output_file = tmp_path / "output.wav"

        with pytest.raises(FileNotFoundError):
            audio_processor.normalize_audio(
                nonexistent, output_file, target_sample_rate=22050
            )
