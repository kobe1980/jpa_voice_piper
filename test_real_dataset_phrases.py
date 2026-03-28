#!/usr/bin/env python3
"""
Test script to synthesize speech using actual phrases from the dataset.
This tests if the model can generate proper-length Japanese sentences.
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
    """
    Synthesize speech from phoneme IDs.

    Args:
        checkpoint_path: Path to the .ckpt file
        phoneme_ids: List of phoneme IDs
        output_wav: Output WAV file path
        noise_scale: Noise scale for generation
        length_scale: Length scale for generation
        noise_scale_w: Noise scale W for generation
    """
    print(f"Loading checkpoint: {checkpoint_path}")
    model = VitsModel.load_from_checkpoint(checkpoint_path, map_location="cpu")
    model.eval()

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
    sample_rate = 22050
    print(f"Saving audio to: {output_wav}")
    sf.write(output_wav, audio, sample_rate)
    print(f"✅ Audio generated successfully!")
    print(f"Duration: {len(audio) / sample_rate:.2f} seconds")
    return audio, sample_rate


def main():
    checkpoint_path = "lightning_logs/version_13/checkpoints/epoch=99-step=91400.ckpt"

    # Load phoneme map
    phoneme_map = load_phoneme_map()
    id_to_char = {v: k for k, v in phoneme_map.items()}

    print("\n" + "="*60)
    print("Testing with Real Dataset Phrases")
    print("="*60 + "\n")

    # Read some samples from metadata_phonemes.csv
    with open('dataset/prepared/metadata_phonemes.csv', 'r', encoding='utf-8') as f:
        # Test first 3 samples
        for i in range(3):
            line = f.readline().strip()
            if not line:
                break

            parts = line.split('|')
            file_id = parts[0]
            phoneme_ids = [int(x) for x in parts[1].split()]

            # Reconstruct text
            text = ''.join([id_to_char.get(pid, '?') for pid in phoneme_ids])

            print(f"\n--- Sample {i+1}: {file_id} ---")
            print(f"Text: {text}")
            print(f"Phonemes: {len(phoneme_ids)}")

            output_file = f"test_dataset_{file_id}.wav"

            try:
                audio, sr = synthesize_from_phoneme_ids(
                    checkpoint_path,
                    phoneme_ids,
                    output_file
                )
                print(f"✅ Success! Play with: afplay {output_file}")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
