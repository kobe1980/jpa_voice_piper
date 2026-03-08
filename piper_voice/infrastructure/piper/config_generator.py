"""Piper config.json generator with custom phoneme mappings.

This module generates Piper-compatible config.json files that include
custom hiragana → phoneme ID mappings for Japanese TTS training.
"""

import json
from pathlib import Path

from piper_voice.core.entities import PhonemeMap


class PiperConfigGenerator:
    """Generator for Piper config.json with custom phoneme mappings.

    Creates configuration files that:
    - Include custom hiragana → phoneme ID mappings
    - Specify audio parameters (sample rate, filter length, etc.)
    - Set inference parameters (noise_scale, length_scale)
    - Flag the config as using custom phonemes
    """

    def generate_config(
        self,
        phoneme_map: PhonemeMap,
        output_path: Path,
        sample_rate: int,
        language: str | None = "ja-jp",
    ) -> None:
        """Generate Piper config.json with custom phoneme mappings.

        Args:
            phoneme_map: PhonemeMap with hiragana → ID mappings
            output_path: Path to save config.json
            sample_rate: Audio sample rate (16000 or 22050)
            language: Language code (default: "ja-jp")

        Raises:
            ValueError: If phoneme_map is empty or sample_rate is invalid
        """
        # Validate inputs
        if len(phoneme_map.phonemes) == 0:
            raise ValueError("PhonemeMap cannot be empty")

        if sample_rate not in (16000, 22050):
            raise ValueError("Sample rate must be 16000 or 22050")

        # Build phoneme mappings dictionary
        phoneme_dict = {
            phoneme.character: phoneme.id for phoneme in phoneme_map.phonemes
        }

        # Create config structure
        config = {
            "num_symbols": len(phoneme_map.phonemes),
            "custom_phonemes": True,
            "language": language,
            "phonemes": phoneme_dict,
            "audio": self._get_audio_params(sample_rate),
            "inference": self._get_inference_params(),
        }

        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write config (pretty-printed)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _get_audio_params(self, sample_rate: int) -> dict:
        """Get Piper audio parameters.

        Args:
            sample_rate: Audio sample rate

        Returns:
            Dictionary of audio parameters
        """
        # Piper default audio parameters
        # These match VITS architecture requirements
        return {
            "sample_rate": sample_rate,
            "filter_length": 1024,
            "hop_length": 256,
            "win_length": 1024,
            "mel_channels": 80,
        }

    def _get_inference_params(self) -> dict:
        """Get Piper inference parameters.

        Returns:
            Dictionary of inference parameters
        """
        # Piper default inference parameters
        # These control voice quality and speed
        return {
            "noise_scale": 0.667,
            "length_scale": 1.0,
            "noise_w": 0.8,
        }
