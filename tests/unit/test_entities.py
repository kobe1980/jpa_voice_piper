"""Unit tests for domain entities.

Following TDD: These tests are written BEFORE implementation.
"""

from pathlib import Path

import pytest

from piper_voice.core.entities import AudioSample, Phoneme, Transcript, Voice
from piper_voice.core.value_objects import (
    AudioFormat,
    AudioQuality,
    Duration,
    SampleRate,
)


class TestAudioSample:
    """Tests for AudioSample entity."""

    def test_create_audio_sample(self) -> None:
        """Test creating an audio sample entity."""
        sample_rate = SampleRate(22050)
        duration = Duration(5.0)
        audio_format = AudioFormat(type="WAV", encoding="PCM_16")
        quality = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.1,
        )

        sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=sample_rate,
            duration=duration,
            format=audio_format,
            quality=quality,
        )

        assert sample.id == "sample_001"
        assert sample.file_path == Path("dataset/raw/sample_001.wav")
        assert sample.sample_rate == sample_rate
        assert sample.duration == duration
        assert sample.format == audio_format
        assert sample.quality == quality

    def test_audio_sample_is_valid(self) -> None:
        """Test audio sample validation."""
        quality_valid = AudioQuality(
            snr_db=35.0,
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.1,
        )

        sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=quality_valid,
        )

        assert sample.is_valid()

    def test_audio_sample_is_invalid(self) -> None:
        """Test audio sample with poor quality is invalid."""
        quality_invalid = AudioQuality(
            snr_db=20.0,  # Below threshold
            max_amplitude=0.85,
            has_clipping=False,
            silence_at_start_sec=0.1,
            silence_at_end_sec=0.1,
        )

        sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=quality_invalid,
        )

        assert not sample.is_valid()


class TestPhoneme:
    """Tests for Phoneme entity."""

    def test_create_phoneme(self) -> None:
        """Test creating a phoneme."""
        phoneme = Phoneme(symbol="a", id=10, language="fr")

        assert phoneme.symbol == "a"
        assert phoneme.id == 10
        assert phoneme.language == "fr"

    def test_phoneme_equality(self) -> None:
        """Test phoneme equality by symbol and language."""
        p1 = Phoneme(symbol="a", id=10, language="fr")
        p2 = Phoneme(symbol="a", id=10, language="fr")
        p3 = Phoneme(symbol="b", id=11, language="fr")

        assert p1 == p2
        assert p1 != p3

    def test_phoneme_equality_with_non_phoneme(self) -> None:
        """Test phoneme comparison with non-Phoneme returns NotImplemented."""
        p = Phoneme(symbol="a", id=10, language="fr")
        result = p.__eq__("not a phoneme")

        assert result == NotImplemented

    def test_phoneme_hashable_in_set(self) -> None:
        """Test that phonemes can be used in sets and dicts (hashable)."""
        p1 = Phoneme(symbol="a", id=10, language="fr")
        p2 = Phoneme(symbol="a", id=10, language="fr")
        p3 = Phoneme(symbol="b", id=11, language="fr")

        phoneme_set = {p1, p2, p3}

        # Same phonemes should result in only 2 unique items
        assert len(phoneme_set) == 2


class TestTranscript:
    """Tests for Transcript entity."""

    def test_create_transcript(self) -> None:
        """Test creating a transcript."""
        transcript = Transcript(
            id="trans_001",
            text="Bonjour, comment allez-vous?",
            phoneme_ids=[1, 2, 3, 4, 5],
            language="fr",
        )

        assert transcript.id == "trans_001"
        assert transcript.text == "Bonjour, comment allez-vous?"
        assert transcript.phoneme_ids == [1, 2, 3, 4, 5]
        assert transcript.language == "fr"

    def test_transcript_normalization(self) -> None:
        """Test text normalization in transcript."""
        transcript = Transcript(
            id="trans_001",
            text="  Bonjour,   comment   allez-vous?  ",
            phoneme_ids=[1, 2, 3],
            language="fr",
        )

        # Text should be normalized (whitespace cleaned)
        assert transcript.normalized_text() == "Bonjour, comment allez-vous?"

    def test_transcript_reject_empty_text(self) -> None:
        """Test that empty text is rejected."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            Transcript(
                id="trans_001",
                text="",
                phoneme_ids=[],
                language="fr",
            )

    def test_transcript_reject_empty_phonemes(self) -> None:
        """Test that empty phoneme list is rejected."""
        with pytest.raises(ValueError, match="Phoneme IDs cannot be empty"):
            Transcript(
                id="trans_001",
                text="Bonjour",
                phoneme_ids=[],
                language="fr",
            )


class TestVoice:
    """Tests for Voice aggregate root."""

    def test_create_voice(self) -> None:
        """Test creating a voice."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        assert voice.id == "fr_FR-custom-medium"
        assert voice.name == "French Custom Voice"
        assert voice.language == "fr"
        assert voice.sample_rate == SampleRate(22050)
        assert voice.quality_level == "medium"
        assert len(voice.samples) == 0

    def test_voice_add_sample(self) -> None:
        """Test adding samples to a voice."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=35.0,
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )

        voice.add_sample(sample)

        assert len(voice.samples) == 1
        assert voice.samples[0] == sample

    def test_voice_reject_sample_with_different_sample_rate(self) -> None:
        """Test that samples with different sample rates are rejected."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(16000),  # Different sample rate
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=35.0,
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )

        with pytest.raises(ValueError, match="Sample rate mismatch"):
            voice.add_sample(sample)

    def test_voice_total_duration(self) -> None:
        """Test calculating total duration of voice samples."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        for i in range(3):
            sample = AudioSample(
                id=f"sample_{i:03d}",
                file_path=Path(f"dataset/raw/sample_{i:03d}.wav"),
                sample_rate=SampleRate(22050),
                duration=Duration(5.0),
                format=AudioFormat(type="WAV", encoding="PCM_16"),
                quality=AudioQuality(
                    snr_db=35.0,
                    max_amplitude=0.85,
                    has_clipping=False,
                    silence_at_start_sec=0.1,
                    silence_at_end_sec=0.1,
                ),
            )
            voice.add_sample(sample)

        assert voice.total_duration_seconds() == 15.0

    def test_voice_valid_sample_count(self) -> None:
        """Test counting valid samples in a voice."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        # Add valid sample
        valid_sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=35.0,
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )
        voice.add_sample(valid_sample)

        # Add invalid sample
        invalid_sample = AudioSample(
            id="sample_002",
            file_path=Path("dataset/raw/sample_002.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=20.0,  # Below threshold
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )
        voice.add_sample(invalid_sample)

        assert voice.valid_sample_count() == 1

    def test_voice_invalid_sample_count(self) -> None:
        """Test counting invalid samples in a voice."""
        voice = Voice(
            id="fr_FR-custom-medium",
            name="French Custom Voice",
            language="fr",
            sample_rate=SampleRate(22050),
            quality_level="medium",
        )

        # Add valid sample
        valid_sample = AudioSample(
            id="sample_001",
            file_path=Path("dataset/raw/sample_001.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=35.0,
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )
        voice.add_sample(valid_sample)

        # Add invalid sample
        invalid_sample = AudioSample(
            id="sample_002",
            file_path=Path("dataset/raw/sample_002.wav"),
            sample_rate=SampleRate(22050),
            duration=Duration(5.0),
            format=AudioFormat(type="WAV", encoding="PCM_16"),
            quality=AudioQuality(
                snr_db=20.0,  # Below threshold
                max_amplitude=0.85,
                has_clipping=False,
                silence_at_start_sec=0.1,
                silence_at_end_sec=0.1,
            ),
        )
        voice.add_sample(invalid_sample)

        assert voice.invalid_sample_count() == 1
