"""Audio processing using librosa and soundfile.

This module implements AudioProcessorPort using librosa for audio analysis
and manipulation, and soundfile for WAV I/O.
"""

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from piper_voice.core.value_objects import AudioQuality


class LibrosaAudioProcessor:
    """Audio processor using librosa and soundfile.

    Implements AudioProcessorPort interface for audio operations.
    """

    def load_audio(self, file_path: Path) -> tuple[list[float], int]:
        """Load audio file and return samples and sample rate.

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (audio_samples, sample_rate)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Load audio with librosa (automatically converts to mono and float)
            audio, sr = librosa.load(file_path, sr=None, mono=True)

            # Convert numpy array to list
            samples = audio.tolist()

            return samples, int(sr)

        except Exception as e:
            raise ValueError(f"Invalid audio file: {file_path}") from e

    def analyze_quality(self, file_path: Path) -> AudioQuality:
        """Analyze audio file and return quality metrics.

        Args:
            file_path: Path to audio file

        Returns:
            AudioQuality value object with all metrics

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        # Load audio
        audio, sr = librosa.load(file_path, sr=None, mono=True)

        # Calculate SNR (Signal-to-Noise Ratio)
        snr_db = self._calculate_snr(audio)

        # Check for clipping
        max_amplitude = float(np.max(np.abs(audio)))
        has_clipping = max_amplitude >= 0.95

        # Measure silence at start and end
        silence_start, silence_end = self._measure_silence(audio, int(sr))

        return AudioQuality(
            snr_db=snr_db,
            max_amplitude=max_amplitude,
            has_clipping=has_clipping,
            silence_at_start_sec=silence_start,
            silence_at_end_sec=silence_end,
        )

    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_sample_rate: int,
    ) -> None:
        """Normalize audio file to target sample rate and format.

        Args:
            input_path: Source audio file
            output_path: Destination audio file
            target_sample_rate: Target sample rate (16000 or 22050)

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If target sample rate is invalid
        """
        # Validate target sample rate
        if target_sample_rate not in (16000, 22050):
            raise ValueError(
                f"Target sample rate must be 16000 or 22050 Hz, "
                f"got {target_sample_rate}"
            )

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Load audio (librosa automatically converts to mono)
        audio, sr = librosa.load(input_path, sr=target_sample_rate, mono=True)

        # Trim silence from start and end (top_db=30 means trim below -30dB)
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=30)

        # Save as WAV 16-bit PCM
        sf.write(output_path, audio_trimmed, target_sample_rate, subtype="PCM_16")

    def _calculate_snr(self, audio: np.ndarray) -> float:
        """Calculate Signal-to-Noise Ratio.

        Uses a simple estimation: assumes the signal is the audio
        and noise is estimated from quieter segments.

        Args:
            audio: Audio samples

        Returns:
            SNR in dB
        """
        # Calculate RMS of signal
        signal_rms = np.sqrt(np.mean(audio**2))

        # Estimate noise from quieter 10% of audio
        audio_sorted = np.sort(np.abs(audio))
        noise_samples = audio_sorted[: int(len(audio_sorted) * 0.1)]
        noise_rms = np.sqrt(np.mean(noise_samples**2))

        # Avoid division by zero
        if noise_rms < 1e-10:
            # Very quiet noise, assume high SNR
            return 60.0

        # Calculate SNR in dB
        snr = 20 * np.log10(signal_rms / noise_rms)

        return float(snr)

    def _measure_silence(
        self, audio: np.ndarray, sample_rate: int, threshold_db: float = -40.0
    ) -> tuple[float, float]:
        """Measure silence duration at start and end of audio.

        Args:
            audio: Audio samples
            sample_rate: Sample rate in Hz
            threshold_db: Threshold in dB for silence detection

        Returns:
            Tuple of (silence_at_start_sec, silence_at_end_sec)
        """
        # Convert threshold from dB to amplitude
        threshold_amplitude = 10 ** (threshold_db / 20)

        # Find first sample above threshold (start)
        above_threshold = np.where(np.abs(audio) > threshold_amplitude)[0]

        if len(above_threshold) == 0:
            # All audio is silent
            total_duration = len(audio) / sample_rate
            return total_duration / 2, total_duration / 2

        first_sound = above_threshold[0]
        last_sound = above_threshold[-1]

        # Calculate silence durations
        silence_start = first_sound / sample_rate
        silence_end = (len(audio) - last_sound - 1) / sample_rate

        return float(silence_start), float(silence_end)
