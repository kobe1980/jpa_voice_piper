"""Unit tests for domain value objects.

Following TDD: These tests are written BEFORE implementation.
"""

import pytest

from piper_voice.core.value_objects import (
    AudioFormat,
    AudioQuality,
    Duration,
    SampleRate,
)


class TestSampleRate:
    """Tests for SampleRate value object."""

    def test_create_valid_sample_rate_16000(self) -> None:
        """Test creating a valid 16000 Hz sample rate."""
        sr = SampleRate(16000)
        assert sr.value == 16000
        assert str(sr) == "16000 Hz"

    def test_create_valid_sample_rate_22050(self) -> None:
        """Test creating a valid 22050 Hz sample rate."""
        sr = SampleRate(22050)
        assert sr.value == 22050
        assert str(sr) == "22050 Hz"

    def test_reject_invalid_sample_rate(self) -> None:
        """Test that invalid sample rates are rejected."""
        with pytest.raises(ValueError, match="Sample rate must be 16000 or 22050"):
            SampleRate(48000)

        with pytest.raises(ValueError, match="Sample rate must be 16000 or 22050"):
            SampleRate(8000)

    def test_sample_rate_equality(self) -> None:
        """Test sample rate equality comparison."""
        sr1 = SampleRate(22050)
        sr2 = SampleRate(22050)
        sr3 = SampleRate(16000)

        assert sr1 == sr2
        assert sr1 != sr3


class TestDuration:
    """Tests for Duration value object."""

    def test_create_valid_duration(self) -> None:
        """Test creating a valid duration."""
        duration = Duration(5.0)
        assert duration.seconds == 5.0
        assert str(duration) == "5.0s"

    def test_reject_duration_too_short(self) -> None:
        """Test that durations under 1 second are rejected."""
        with pytest.raises(
            ValueError, match="Duration must be between 1 and 15 seconds"
        ):
            Duration(0.5)

    def test_reject_duration_too_long(self) -> None:
        """Test that durations over 15 seconds are rejected."""
        with pytest.raises(
            ValueError, match="Duration must be between 1 and 15 seconds"
        ):
            Duration(20.0)

    def test_reject_negative_duration(self) -> None:
        """Test that negative durations are rejected."""
        with pytest.raises(
            ValueError, match="Duration must be between 1 and 15 seconds"
        ):
            Duration(-1.0)

    def test_duration_equality(self) -> None:
        """Test duration equality comparison."""
        d1 = Duration(5.0)
        d2 = Duration(5.0)
        d3 = Duration(10.0)

        assert d1 == d2
        assert d1 != d3


class TestAudioFormat:
    """Tests for AudioFormat value object."""

    def test_create_wav_pcm16(self) -> None:
        """Test creating WAV PCM_16 format."""
        fmt = AudioFormat(type="WAV", encoding="PCM_16")
        assert fmt.type == "WAV"
        assert fmt.encoding == "PCM_16"
        assert str(fmt) == "WAV PCM_16"

    def test_reject_invalid_format_type(self) -> None:
        """Test that non-WAV formats are rejected."""
        with pytest.raises(ValueError, match="Only WAV format is supported"):
            AudioFormat(type="MP3", encoding="PCM_16")

    def test_reject_invalid_encoding(self) -> None:
        """Test that non-PCM_16 encodings are rejected."""
        with pytest.raises(ValueError, match="Only PCM_16 encoding is supported"):
            AudioFormat(type="WAV", encoding="PCM_24")

    def test_format_equality(self) -> None:
        """Test audio format equality comparison."""
        fmt1 = AudioFormat(type="WAV", encoding="PCM_16")
        fmt2 = AudioFormat(type="WAV", encoding="PCM_16")

        assert fmt1 == fmt2


class TestAudioQuality:
    """Tests for AudioQuality value object."""

    def test_create_valid_audio_quality(self) -> None:
        """Test creating valid audio quality metrics."""
        quality = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.15,
        )

        assert quality.snr_db == 35.0
        assert quality.max_amplitude == 0.85
        assert not quality.has_clipping
        assert quality.silence_at_start_sec == 0.1
        assert quality.silence_at_end_sec == 0.15

    def test_validate_snr_below_threshold(self) -> None:
        """Test validation fails when SNR is below 30 dB."""
        quality = AudioQuality(
            snr_db=25.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.1,
        )

        is_valid, errors = quality.validate()
        assert not is_valid
        assert any("SNR" in error for error in errors)

    def test_validate_clipping_detected(self) -> None:
        """Test validation fails when clipping is detected."""
        quality = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.98,
            has_clipping=True,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.1,
        )

        is_valid, errors = quality.validate()
        assert not is_valid
        assert any("clipping" in error.lower() for error in errors)

    def test_validate_excessive_silence(self) -> None:
        """Test validation fails when silence is excessive."""
        quality = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.5,
            silence_at_end_sec=0.5,
        )

        is_valid, errors = quality.validate()
        assert not is_valid
        assert any("silence" in error.lower() for error in errors)

    def test_validate_all_pass(self) -> None:
        """Test validation passes when all criteria are met."""
        quality = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.15,
        )

        is_valid, errors = quality.validate()
        assert is_valid
        assert len(errors) == 0

    def test_validate_multiple_failures(self) -> None:
        """Test validation reports all failures."""
        quality = AudioQuality(
            snr_db=20.0,  # Too low
            max_amplitude=0.98,  # Too high
            has_clipping=True,  # Clipping detected
            silence_at_start_sec=0.5,  # Too much
            silence_at_end_sec=0.5,  # Too much
        )

        is_valid, errors = quality.validate()
        assert not is_valid
        assert len(errors) >= 3  # At least SNR, clipping, and silence
