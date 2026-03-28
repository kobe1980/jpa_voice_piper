#!/usr/bin/env python3
"""
Test script with adjusted length_scale to fix short duration issue.

Based on comparison:
- Original JSUT audio: 3.19 seconds
- Generated audio (length_scale=1.0): 0.37 seconds
- Ratio: 8.6x too fast

Solution: Use length_scale = 8.0 to 10.0
"""

import sys
from pathlib import Path
import json
import torch
import soundfile as sf

# Add piper-training to path
sys.path.insert(0, str(Path(__file__).parent / "piper-training" / "src"))

from piper.train.vits.lightning import VitsModel


def load_phoneme_map(phoneme_map_path: str = "dataset/prepared/phoneme_map.json"):
    """Load phoneme map from JSON file."""
    with open(phoneme_map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['phonemes']


def synthesize_from_phoneme_ids(
    checkpoint_path: str,
    phoneme_ids: list[int],
    output_wav: str,
    noise_scale: float = 0.667,
    length_scale: float = 1.0,
    noise_scale_w: float = 0.8
):
    """Synthesize speech from phoneme IDs with custom parameters."""
    print(f"Loading checkpoint: {checkpoint_path}")
    model = VitsModel.load_from_checkpoint(checkpoint_path, map_location="cpu")
    model.eval()

    print(f"Synthesizing {len(phoneme_ids)} phonemes with length_scale={length_scale}...")

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
        audio = result[0][0, 0].cpu().numpy()

    # Save to WAV file
    sample_rate = 22050
    print(f"Saving audio to: {output_wav}")
    sf.write(output_wav, audio, sample_rate)
    duration = len(audio) / sample_rate
    print(f"✅ Audio generated successfully!")
    print(f"Duration: {duration:.2f} seconds")
    return audio, sample_rate


def main():
    checkpoint_path = "lightning_logs/version_13/checkpoints/epoch=99-step=91400.ckpt"

    # Load phoneme map
    phoneme_map = load_phoneme_map()
    id_to_char = {v: k for k, v in phoneme_map.items()}

    print("\n" + "="*80)
    print("Testing with ADJUSTED length_scale")
    print("="*80)
    print()
    print("Original issue:")
    print("  - JSUT audio: 3.19 seconds")
    print("  - Generated (length_scale=1.0): 0.37 seconds")
    print("  - Ratio: 8.6x too fast")
    print()
    print("Testing different length_scale values...")
    print("="*80 + "\n")

    # Read first sample from metadata_phonemes.csv
    with open('dataset/prepared/metadata_phonemes.csv', 'r', encoding='utf-8') as f:
        line = f.readline().strip()

    parts = line.split('|')
    file_id = parts[0]
    phoneme_ids = [int(x) for x in parts[1].split()]
    text = ''.join([id_to_char.get(pid, '?') for pid in phoneme_ids])

    print(f"Test phrase: {text}")
    print(f"File ID: {file_id}")
    print(f"Phonemes: {len(phoneme_ids)}")
    print(f"Original JSUT duration: 3.19 seconds")
    print()

    # Test different length_scale values
    test_scales = [
        (1.0, "baseline"),
        (2.0, "2x_slower"),
        (4.0, "4x_slower"),
        (6.0, "6x_slower"),
        (8.0, "8x_slower"),
        (10.0, "10x_slower"),
    ]

    for scale, label in test_scales:
        output_file = f"test_length_{label}.wav"
        print(f"\n--- Test length_scale={scale} ({label}) ---")

        try:
            audio, sr = synthesize_from_phoneme_ids(
                checkpoint_path,
                phoneme_ids,
                output_file,
                length_scale=scale
            )
            duration = len(audio) / sr
            ratio_to_original = duration / 3.19
            print(f"✅ Success!")
            print(f"   Duration: {duration:.2f}s (ratio to original: {ratio_to_original:.1%})")
            print(f"   Play with: afplay {output_file}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "="*80)
    print("Testing complete!")
    print()
    print("Recommendation:")
    print("  Listen to each file and choose the best length_scale")
    print("  Expected: length_scale ≈ 8.0-10.0 for natural speed")
    print("="*80)


if __name__ == "__main__":
    main()
