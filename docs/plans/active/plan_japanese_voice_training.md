# Plan : Entraînement d'une voix japonaise Piper TTS

**STATUS** : 📋 PLANNED (projet séparé)
**Date de création** : 2026-03-08
**Priorité** : BASSE (projet d'apprentissage long terme)
**Durée estimée** : 1-2 semaines
**Repo** : `piper-japanese-voice` (nouveau repo dédié)

---

## 🎯 Objectif

Entraîner une voix japonaise Piper TTS de qualité moyenne à partir du corpus JSUT, utilisable dans le projet IPA pour la synthèse vocale multilingue.

---

## 📁 Arborescence du projet

```
piper-japanese-voice/
├── README.md                      # Documentation principale
├── LICENSE                        # MIT ou autre
├── .gitignore                     # Python + data files
├── pyproject.toml                 # Dépendances Python
├── requirements.txt               # Alternative pip
│
├── docs/
│   ├── TRAINING.md               # Guide d'entraînement détaillé
│   ├── PHONEMIZATION.md          # Documentation phonétique japonaise
│   ├── TROUBLESHOOTING.md        # Solutions aux problèmes courants
│   └── ARCHITECTURE.md           # Architecture VITS/Piper
│
├── scripts/
│   ├── 00_setup.sh               # Installation de l'environnement
│   ├── 01_download_jsut.sh       # Téléchargement corpus JSUT
│   ├── 02_prepare_dataset.py     # Préparation des données
│   ├── 03_phonemize.py           # Conversion texte → phonèmes
│   ├── 04_train.sh               # Script d'entraînement principal
│   ├── 05_export.sh              # Export vers ONNX
│   ├── 06_test_voice.py          # Test de la voix générée
│   └── utils/
│       ├── audio_processing.py   # Normalisation audio
│       ├── text_cleaning.py      # Nettoyage texte japonais
│       └── phoneme_mapping.py    # Mapping phonèmes japonais
│
├── configs/
│   ├── training_config.yaml      # Config entraînement Piper
│   ├── phoneme_map.json          # Map phonèmes → IDs
│   └── dataset_config.json       # Config du dataset
│
├── data/                          # Données (gitignored)
│   ├── raw/
│   │   └── jsut_ver1.1/         # Corpus JSUT téléchargé
│   ├── processed/
│   │   ├── metadata.csv         # Audio paths + texte
│   │   ├── metadata_phonemes.csv # Audio paths + phonèmes
│   │   └── wavs/                # Audio normalisé 22050Hz
│   └── cache/                   # Cache Piper
│
├── checkpoints/                   # Checkpoints (gitignored)
│   ├── pretrained/               # Checkpoints de départ
│   │   └── fr_FR-siwis-medium.ckpt
│   └── training/                 # Checkpoints pendant training
│       └── epoch_*.ckpt
│
├── models/                        # Modèles exportés
│   ├── ja_JP-jsut-medium.onnx
│   └── ja_JP-jsut-medium.onnx.json
│
├── tests/
│   ├── test_phonemization.py     # Tests unitaires phonémisation
│   ├── test_audio_processing.py  # Tests traitement audio
│   └── test_voice_quality.py     # Tests qualité voix
│
└── notebooks/                     # Jupyter notebooks (optionnel)
    ├── 01_explore_jsut.ipynb     # Exploration du corpus
    ├── 02_analyze_phonemes.ipynb # Analyse phonétique
    └── 03_evaluate_model.ipynb   # Évaluation du modèle
```

---

## 📋 Plan d'implémentation détaillé

### Phase 0 : Setup initial (1h)

**Tâches** :
1. Créer repo GitHub `piper-japanese-voice`
2. Créer l'arborescence de base
3. Initialiser pyproject.toml avec dépendances
4. Créer README.md avec description du projet
5. Créer .gitignore pour exclure data/ et checkpoints/

**Livrables** :
- Repo GitHub initialisé
- Structure de dossiers créée
- README basique
- pyproject.toml avec dépendances

**Validation** :
```bash
git clone https://github.com/[USER]/piper-japanese-voice.git
cd piper-japanese-voice
ls -la  # Vérifier structure
```

---

### Phase 1 : Installation de l'environnement (2h)

**Tâches** :
1. Créer script `scripts/00_setup.sh`
2. Installer Python 3.11+
3. Créer venv
4. Installer piper-training depuis GitHub
5. Compiler monotonic_align extension
6. Installer librosa, torch, etc.
7. Vérifier installation GPU/MPS

**Script `scripts/00_setup.sh`** :
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Setting up Piper Japanese Voice training environment..."

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch (MPS for Mac M1/M2/M3)
pip install torch torchvision torchaudio

# Clone Piper training
git clone https://github.com/OHF-voice/piper1-gpl.git piper-training
cd piper-training
pip install -e '.[train]'

# Build monotonic_align
./build_monotonic_align.sh

# Install additional dependencies
pip install librosa pydub pandas tqdm pyyaml

# Verify installation
python3 -c "import piper.train; print('✅ Piper training installed')"
python3 -c "import torch; print(f'✅ PyTorch installed (MPS: {torch.backends.mps.is_available()})')"

echo "✅ Setup complete!"
```

**Livrables** :
- Environment Python fonctionnel
- Piper training installé
- Extensions compilées

**Validation** :
```bash
./scripts/00_setup.sh
source .venv/bin/activate
python3 -c "import piper.train; print('OK')"
```

---

### Phase 2 : Téléchargement du corpus JSUT (3h)

**Tâches** :
1. Créer script `scripts/01_download_jsut.sh`
2. Télécharger JSUT corpus (~2GB)
3. Extraire archive
4. Vérifier intégrité des fichiers
5. Générer statistiques du corpus

**Script `scripts/01_download_jsut.sh`** :
```bash
#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="data/raw"
mkdir -p "$DATA_DIR"

echo "📥 Downloading JSUT corpus..."

# JSUT corpus URL
JSUT_URL="https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut_ver1.1.zip"

# Download
curl -L -o "$DATA_DIR/jsut_ver1.1.zip" "$JSUT_URL"

# Extract
echo "📦 Extracting..."
unzip "$DATA_DIR/jsut_ver1.1.zip" -d "$DATA_DIR/"

# Verify
echo "✅ Verifying files..."
AUDIO_COUNT=$(find "$DATA_DIR/jsut_ver1.1" -name "*.wav" | wc -l)
echo "   Found $AUDIO_COUNT audio files"

if [[ $AUDIO_COUNT -lt 7000 ]]; then
    echo "❌ Error: Expected ~7000 files, found $AUDIO_COUNT"
    exit 1
fi

echo "✅ JSUT corpus ready!"
echo "   Location: $DATA_DIR/jsut_ver1.1/"
```

**Corpus JSUT** :
- **Source** : Université de Tokyo
- **Taille** : ~10 heures de parole
- **Locutrice** : 1 femme japonaise
- **Qualité** : Studio, 48kHz
- **Contenu** : Phrases de base en japonais
- **License** : CC BY-SA 4.0

**Livrables** :
- Corpus JSUT téléchargé
- ~7300 fichiers .wav
- Transcriptions en japonais

**Validation** :
```bash
./scripts/01_download_jsut.sh
ls data/raw/jsut_ver1.1/ | head
```

---

### Phase 3 : Préparation du dataset (4h)

**Tâches** :
1. Créer script `scripts/02_prepare_dataset.py`
2. Normaliser audio à 22050Hz mono
3. Nettoyer les transcriptions
4. Créer metadata.csv
5. Valider format CSV

**Script `scripts/02_prepare_dataset.py`** :
```python
#!/usr/bin/env python3
"""Prepare JSUT corpus for Piper training."""

import csv
import re
from pathlib import Path
from typing import List, Tuple

import librosa
import soundfile as sf
from tqdm import tqdm


def clean_japanese_text(text: str) -> str:
    """Clean Japanese text for TTS."""
    # Remove reading hints (furigana)
    text = re.sub(r'\(.*?\)', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def normalize_audio(
    input_path: Path,
    output_path: Path,
    target_sr: int = 22050
) -> None:
    """Normalize audio to target sample rate and mono."""
    # Load audio
    audio, sr = librosa.load(input_path, sr=target_sr, mono=True)

    # Trim silence
    audio, _ = librosa.effects.trim(audio, top_db=30)

    # Save normalized
    sf.write(output_path, audio, target_sr)


def prepare_dataset(
    jsut_dir: Path,
    output_dir: Path,
    target_sr: int = 22050
) -> List[Tuple[str, str]]:
    """Prepare JSUT corpus for training."""

    # Find transcript files
    transcript_files = list(jsut_dir.rglob("transcript_utf8.txt"))

    metadata = []
    wavs_dir = output_dir / "wavs"
    wavs_dir.mkdir(parents=True, exist_ok=True)

    print(f"📝 Processing {len(transcript_files)} transcript files...")

    for transcript_file in tqdm(transcript_files):
        # Read transcripts
        with open(transcript_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Format: BASIC5000_0001:あいうえお
                if ':' not in line:
                    continue

                audio_id, text = line.strip().split(':', 1)

                # Find corresponding audio
                audio_file = transcript_file.parent / f"{audio_id}.wav"
                if not audio_file.exists():
                    continue

                # Clean text
                text = clean_japanese_text(text)
                if not text:
                    continue

                # Normalize audio
                output_audio = wavs_dir / f"{audio_id}.wav"
                normalize_audio(audio_file, output_audio, target_sr)

                # Add to metadata
                metadata.append((f"{audio_id}.wav", text))

    return metadata


def write_metadata(
    metadata: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """Write metadata CSV."""
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='|')
        for audio_file, text in metadata:
            writer.writerow([audio_file, text])


if __name__ == "__main__":
    jsut_dir = Path("data/raw/jsut_ver1.1")
    output_dir = Path("data/processed")

    print("🔄 Preparing JSUT dataset...")
    metadata = prepare_dataset(jsut_dir, output_dir)

    print(f"✅ Processed {len(metadata)} utterances")

    # Write metadata
    metadata_path = output_dir / "metadata.csv"
    write_metadata(metadata, metadata_path)

    print(f"✅ Metadata saved to {metadata_path}")
    print(f"   Format: audio.wav|Japanese text")
```

**Livrables** :
- Audio normalisé 22050Hz mono
- metadata.csv avec format correct
- ~7000 paires audio/texte

**Validation** :
```bash
python3 scripts/02_prepare_dataset.py
head data/processed/metadata.csv
```

---

### Phase 4 : Phonémisation japonaise (6h)

**Challenge** : espeak-ng ne supporte pas bien le japonais.

**Solution** : Utiliser les **hiragana comme phonèmes** (approche simple et efficace).

**Tâches** :
1. Créer script `scripts/03_phonemize.py`
2. Convertir kanji → hiragana (avec pykakasi)
3. Créer phoneme_map.json
4. Générer metadata_phonemes.csv

**Script `scripts/03_phonemize.py`** :
```python
#!/usr/bin/env python3
"""Phonemize Japanese text using hiragana."""

import csv
import json
from pathlib import Path
from typing import Dict, List

import pykakasi


def create_phoneme_map(metadata_path: Path) -> Dict[str, int]:
    """Create phoneme → ID mapping from all unique hiragana."""

    # Read all texts
    texts = []
    with open(metadata_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            if len(row) >= 2:
                texts.append(row[1])

    # Convert to hiragana
    kks = pykakasi.kakasi()
    all_phonemes = set()

    for text in texts:
        result = kks.convert(text)
        hiragana = ''.join([item['hira'] for item in result])
        all_phonemes.update(list(hiragana))

    # Create mapping (sorted for consistency)
    phoneme_map = {
        '<pad>': 0,
        '<bos>': 1,
        '<eos>': 2,
    }

    for i, phoneme in enumerate(sorted(all_phonemes), start=3):
        phoneme_map[phoneme] = i

    return phoneme_map


def phonemize_metadata(
    input_path: Path,
    output_path: Path,
    phoneme_map: Dict[str, int]
) -> None:
    """Convert metadata to phoneme IDs."""

    kks = pykakasi.kakasi()

    with open(input_path, 'r', encoding='utf-8') as fin:
        with open(output_path, 'w', encoding='utf-8', newline='') as fout:
            reader = csv.reader(fin, delimiter='|')
            writer = csv.writer(fout, delimiter='|')

            for row in reader:
                if len(row) < 2:
                    continue

                audio_file, text = row[0], row[1]

                # Convert to hiragana
                result = kks.convert(text)
                hiragana = ''.join([item['hira'] for item in result])

                # Convert to phoneme IDs
                phoneme_ids = [phoneme_map.get(char, 0) for char in hiragana]
                phoneme_ids_str = ' '.join(map(str, phoneme_ids))

                # Write: audio.wav|Original text|phoneme IDs
                writer.writerow([audio_file, text, phoneme_ids_str])


if __name__ == "__main__":
    input_path = Path("data/processed/metadata.csv")
    output_path = Path("data/processed/metadata_phonemes.csv")
    phoneme_map_path = Path("configs/phoneme_map.json")

    print("🔤 Creating phoneme map...")
    phoneme_map = create_phoneme_map(input_path)

    print(f"   Found {len(phoneme_map)} unique phonemes")

    # Save phoneme map
    phoneme_map_path.parent.mkdir(exist_ok=True)
    with open(phoneme_map_path, 'w', encoding='utf-8') as f:
        json.dump(phoneme_map, f, ensure_ascii=False, indent=2)

    print(f"✅ Phoneme map saved to {phoneme_map_path}")

    # Phonemize metadata
    print("🔤 Phonemizing metadata...")
    phonemize_metadata(input_path, output_path, phoneme_map)

    print(f"✅ Phonemized metadata saved to {output_path}")
```

**Dépendances** :
```bash
pip install pykakasi
```

**Livrables** :
- phoneme_map.json (~100 phonèmes hiragana)
- metadata_phonemes.csv avec IDs phonétiques

**Validation** :
```bash
python3 scripts/03_phonemize.py
cat configs/phoneme_map.json | head -20
```

---

### Phase 5 : Téléchargement checkpoint (1h)

**Tâches** :
1. Télécharger checkpoint français `fr_FR-siwis-medium`
2. Placer dans `checkpoints/pretrained/`

**Script** :
```bash
#!/usr/bin/env bash
# scripts/download_checkpoint.sh

mkdir -p checkpoints/pretrained

echo "📥 Downloading French checkpoint for fine-tuning..."

curl -L -o checkpoints/pretrained/fr_FR-siwis-medium.ckpt \
  "https://huggingface.co/rhasspy/piper-checkpoints/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.ckpt"

echo "✅ Checkpoint ready!"
```

---

### Phase 6 : Entraînement (2-5 jours)

**Script `scripts/04_train.sh`** :
```bash
#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

python3 -m piper.train fit \
  --data.voice_name "ja_JP-jsut-medium" \
  --data.csv_path data/processed/metadata_phonemes.csv \
  --data.audio_dir data/processed/wavs/ \
  --model.sample_rate 22050 \
  --data.data_type phoneme_ids \
  --data.num_symbols 120 \
  --data.phonemes_path configs/phoneme_map.json \
  --data.cache_dir data/cache/ \
  --data.config_path models/ja_JP-jsut-medium.onnx.json \
  --data.batch_size 16 \
  --trainer.max_epochs 1000 \
  --trainer.check_val_every_n_epoch 10 \
  --trainer.log_every_n_steps 100 \
  --ckpt_path checkpoints/pretrained/fr_FR-siwis-medium.ckpt
```

**Monitoring** :
```bash
# Tensorboard
tensorboard --logdir lightning_logs/
```

---

### Phase 7 : Export et test (2h)

**Script `scripts/05_export.sh`** :
```bash
#!/usr/bin/env bash

source .venv/bin/activate

# Find best checkpoint
BEST_CKPT=$(ls -t checkpoints/training/*.ckpt | head -1)

echo "📤 Exporting $BEST_CKPT to ONNX..."

python3 -m piper.train.export_onnx \
  --checkpoint "$BEST_CKPT" \
  --output-file models/ja_JP-jsut-medium.onnx

echo "✅ Model exported!"
echo "   Model: models/ja_JP-jsut-medium.onnx"
echo "   Config: models/ja_JP-jsut-medium.onnx.json"
```

**Script de test `scripts/06_test_voice.py`** :
```python
#!/usr/bin/env python3
"""Test the trained Japanese voice."""

import wave
from pathlib import Path

import numpy as np
import onnxruntime as ort


def synthesize(
    text: str,
    model_path: Path,
    config_path: Path,
    output_path: Path
) -> None:
    """Synthesize speech from text."""

    # Load model
    session = ort.InferenceSession(str(model_path))

    # TODO: Implement full synthesis pipeline
    # (simplified here for brevity)

    print(f"✅ Synthesized: {output_path}")


if __name__ == "__main__":
    test_texts = [
        "こんにちは",
        "ありがとうございます",
        "さようなら",
    ]

    model_path = Path("models/ja_JP-jsut-medium.onnx")
    config_path = Path("models/ja_JP-jsut-medium.onnx.json")

    for i, text in enumerate(test_texts):
        output_path = Path(f"test_output_{i}.wav")
        synthesize(text, model_path, config_path, output_path)
```

---

## 📊 Métriques de succès

### Qualité audio
- [ ] Intelligibilité > 80% (test avec natifs)
- [ ] Naturalité > 60% (MOS score)
- [ ] Pas d'artefacts audibles

### Performance
- [ ] Temps de synthèse < 1s pour 10 mots
- [ ] Modèle ONNX < 100MB

### Intégration
- [ ] Compatible avec IPA MultilingualTTSAdapter
- [ ] Fonctionne avec piper-cli

---

## 🔗 Intégration dans IPA

Une fois la voix entraînée :

**Dans le projet IPA** :
```bash
# Copier les fichiers
cp piper-japanese-voice/models/ja_JP-jsut-medium.onnx* \
   IPA/data/piper/voices/

# Modifier assistant/__main__.py
voice_map = {
    "fr": "fr_FR-siwis-medium",
    "en": "en_US-amy-medium",
    "ja": "ja_JP-jsut-medium",  # ← Ajouter
}
```

---

## 📚 Documentation à créer

### README.md principal
- Objectif du projet
- Instructions d'installation
- Guide rapide
- Liens vers ressources

### TRAINING.md
- Guide détaillé étape par étape
- Paramètres d'entraînement expliqués
- Troubleshooting

### PHONEMIZATION.md
- Explication du système hiragana
- Alternatives (OpenJTalk, espeak)
- Choix de design

### ARCHITECTURE.md
- Architecture VITS
- Modifications pour le japonais
- Flow de données

---

## ⏱️ Timeline estimée

| Phase | Durée | Activité |
|-------|-------|----------|
| 0 | 1h | Setup repo |
| 1 | 2h | Installation environnement |
| 2 | 3h | Téléchargement JSUT |
| 3 | 4h | Préparation dataset |
| 4 | 6h | Phonémisation |
| 5 | 1h | Téléchargement checkpoint |
| 6 | 2-5 jours | **Entraînement** |
| 7 | 2h | Export et test |
| **TOTAL** | **1-2 semaines** | |

---

## 🚀 Prochaines étapes

Quand tu voudras démarrer ce projet :

1. **Créer le repo GitHub** `piper-japanese-voice`
2. **Me donner l'URL du repo**
3. **Je clone et implémente toute l'arborescence from scratch**
4. **Tu lances les scripts dans l'ordre**
5. **Monitoring de l'entraînement**
6. **Intégration dans IPA**

---

## 💡 Notes importantes

- **GPU recommandé** : Mac M1/M2/M3 avec MPS ok, mais plus lent
- **Espace disque** : ~30GB nécessaires
- **Temps d'entraînement** : Variable selon hardware
- **Qualité** : Premier modèle sera imparfait, itérations nécessaires
- **Alternative** : Si entraînement trop long, on peut toujours revenir à MacOSTTS

---

## 📖 Ressources

- [Piper Training](https://github.com/OHF-voice/piper1-gpl)
- [JSUT Corpus](https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut-corpus)
- [VITS Paper](https://arxiv.org/abs/2106.06103)
- [pykakasi](https://github.com/miurahr/pykakasi)
