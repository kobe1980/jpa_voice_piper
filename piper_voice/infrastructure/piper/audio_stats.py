"""Audio normalization statistics calculator for Piper preprocessing.

This module calculates mean, std, min, max across all audio files
for use in Piper TTS training normalization.
"""

import json
import wave
from pathlib import Path

import numpy as np


class AudioStatsCalculator:
    """Calculator for audio normalization statistics.

    Computes statistics across a dataset of audio files for
    use in Piper training normalization pipeline.
    """

    def calculate_stats(
        self,
        audio_files: list[Path],
        expected_sample_rate: int | None = None,
    ) -> dict:
        """Calculate normalization statistics across audio files.

        Args:
            audio_files: List of WAV file paths
            expected_sample_rate: Optional sample rate validation (16000 or 22050)

        Returns:
            Dictionary with mean, std, min, max, sample_count

        Raises:
            ValueError: If no files provided or sample rate validation fails
            FileNotFoundError: If audio file doesn't exist
        """
        if not audio_files:
            raise ValueError("No audio files provided")

        all_samples = []
        total_samples = 0

        for audio_file in audio_files:
            if not audio_file.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_file}")

            # Load audio samples
            with wave.open(str(audio_file), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                num_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()

                # Validate sample rate if specified
                if expected_sample_rate is not None:
                    if sample_rate != expected_sample_rate:
                        raise ValueError(
                            f"Sample rate must be {expected_sample_rate} Hz, "
                            f"got {sample_rate} Hz in {audio_file.name}"
                        )

                # Read frames
                num_frames = wav_file.getnframes()
                frames = wav_file.readframes(num_frames)

                # Convert to numpy array
                if sample_width == 2:  # 16-bit PCM
                    samples = np.frombuffer(frames, dtype=np.int16)
                else:
                    raise ValueError(
                        f"Unsupported sample width: {sample_width} bytes "
                        f"(expected 2 bytes for 16-bit PCM)"
                    )

                # Handle stereo → mono if needed
                if num_channels == 2:
                    samples = samples.reshape(-1, 2).mean(axis=1)

                # Normalize to [-1, 1] range
                samples_normalized = samples.astype(np.float32) / 32768.0

                all_samples.append(samples_normalized)
                total_samples += len(samples_normalized)

        # Concatenate all samples
        all_samples_array = np.concatenate(all_samples)

        # Calculate statistics
        stats = {
            "mean": float(np.mean(all_samples_array)),
            "std": float(np.std(all_samples_array)),
            "min": float(np.min(all_samples_array)),
            "max": float(np.max(all_samples_array)),
            "sample_count": total_samples,
        }

        return stats

    def save_stats(self, stats: dict, output_path: Path) -> None:
        """Save statistics to JSON file.

        Args:
            stats: Statistics dictionary
            output_path: Path to save JSON
        """
        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON (pretty-printed)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
