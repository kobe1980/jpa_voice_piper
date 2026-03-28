#!/usr/bin/env python3
"""
Test script to synthesize speech from the trained Japanese voice model.
Uses the correct phoneme mapping from hiragana characters.
"""

import sys
from pathlib import Path
import json
import torch
import numpy as np
import soundfile as sf

# Add piper-training to path
sys.path.insert(0, str(Path(__file__).parent / "piper-training" / "src"))

from piper.train.vits.lightning import VitsModel


def load_phoneme_map(phoneme_map_path: str = "dataset/prepared/phoneme_map.json"):
    """Load phoneme map from JSON file."""
    with open(phoneme_map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['phonemes']


def text_to_phoneme_ids(text: str, phoneme_map: dict) -> list[int]:
    """Convert Japanese text (hiragana) to phoneme IDs."""
    return [phoneme_map.get(char, 0) for char in text]


def synthesize_text(
    checkpoint_path: str,
    text: str,
    phoneme_map: dict,
    output_wav: str,
    noise_scale: float = 0.667,
    length_scale: float = 1.0,
    noise_scale_w: float = 0.8
):
    """
    Synthesize speech from Japanese text.

    Args:
        checkpoint_path: Path to the .ckpt file
        text: Japanese text in hiragana
        phoneme_map: Phoneme mapping dictionary
        output_wav: Output WAV file path
        noise_scale: Noise scale for generation (default: 0.667)
        length_scale: Length scale for generation (default: 1.0)
        noise_scale_w: Noise scale W for generation (default: 0.8)
    """
    print(f"Loading checkpoint: {checkpoint_path}")
    model = VitsModel.load_from_checkpoint(checkpoint_path, map_location="cpu")
    model.eval()

    # Convert text to phoneme IDs
    phoneme_ids = text_to_phoneme_ids(text, phoneme_map)
    print(f"Text: {text}")
    print(f"Phoneme IDs: {phoneme_ids}")
    print(f"Synthesizing {len(phoneme_ids)} phonemes...")

    # Prepare input tensors
    text_tensor = torch.LongTensor(phoneme_ids).unsqueeze(0)
    text_lengths = torch.LongTensor([len(phoneme_ids)])

    # Generate audio
    with torch.no_grad():
        result = model.model_g.infer(
            text_tensor,
            text_lengths,
            noise_scale=noise_scale,
            length_scale=length_scale,
            noise_scale_w=noise_scale_w
        )
        # Result is a tuple (audio, attn, mask, (z, z_p, z_hat))
        audio = result[0][0, 0].cpu().numpy()

    # Save to WAV file
    # Use default sample rate from JSUT preprocessing (22050 Hz)
    sample_rate = 22050
    print(f"Saving audio to: {output_wav} (sample_rate={sample_rate})")
    sf.write(output_wav, audio, sample_rate)
    print(f"✅ Audio generated successfully!")
    print(f"Duration: {len(audio) / sample_rate:.2f} seconds")
    return audio, sample_rate


def main():
    checkpoint_path = "lightning_logs/version_13/checkpoints/epoch=99-step=91400.ckpt"

    # Load phoneme map
    phoneme_map = load_phoneme_map()
    print(f"Loaded phoneme map with {len(phoneme_map)} phonemes")

    # Test phrases
    test_phrases = [
        ("こんにちは", "test_konnichiwa.wav"),  # Hello
        ("ありがとう", "test_arigatou.wav"),    # Thank you
        ("おはよう", "test_ohayou.wav"),        # Good morning
        ("さようなら", "test_sayounara.wav"),   # Goodbye
    ]

    print("\n" + "="*60)
    print("Testing Japanese TTS Model")
    print("="*60 + "\n")

    for text, output_file in test_phrases:
        try:
            print(f"\n--- Test: {text} ---")
            audio, sr = synthesize_text(
                checkpoint_path,
                text,
                phoneme_map,
                output_file
            )
            print(f"✅ Success! Play with: afplay {output_file}")
        except Exception as e:
            print(f"❌ Error synthesizing '{text}': {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
