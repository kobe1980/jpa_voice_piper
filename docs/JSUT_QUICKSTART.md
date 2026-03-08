# Guide Rapide : Créer une Voix Japonaise avec JSUT

Ce guide vous montre comment créer un modèle de voix japonaise de A à Z en utilisant le corpus **JSUT** (Japanese Speech corpus, ~7,300 phrases gratuites).

## Vue d'ensemble

```
JSUT corpus → Préparation → Phonétisation → Preprocessing → Training → Export ONNX
  (~10 GB)      (~1h)         (~5 min)        (~10 min)      (1-3 jours)   (~1 min)
```

## Étape 1 : Télécharger le corpus JSUT

### Option A : Script automatique (recommandé)

```bash
./scripts/download_jsut.sh
```

Le script vous propose de choisir :
1. **basic5000** (5,000 phrases) - Recommandé pour démarrer
2. onomatopoeic5000 (5,000 onomatopées)
3. voiceactress100 (100 phrases émotionnelles)
4. all (dataset complet)

### Option B : Téléchargement manuel

```bash
mkdir -p dataset/jsut
cd dataset/jsut

# Télécharger JSUT
# Note: JSUT corpus est hébergé sur le serveur de l'Université de Tokyo
wget http://ss-takashi.sakura.ne.jp/corpus/jsut_ver1.1.zip

# Extraire
unzip jsut_ver1.1.zip
mv jsut_ver1.1/* .
rm -rf jsut_ver1.1 jsut_ver1.1.zip

cd ../..
```

**Structure obtenue** :
```
dataset/jsut/
├── basic5000/
│   ├── wav/              # 5,000 fichiers WAV
│   │   ├── BASIC5000_0001.wav
│   │   ├── BASIC5000_0002.wav
│   │   └── ...
│   └── transcript_utf8.txt  # Transcriptions japonaises
├── onomatopoeic5000/
├── voiceactress100/
└── ...
```

## Étape 2 : Préparer le dataset

Cette étape :
- ✅ Charge les audios JSUT (48 kHz)
- ✅ Convertit à 22050 Hz (format Piper)
- ✅ Valide la qualité audio (SNR, clipping, silence)
- ✅ Crée `metadata.csv` avec les transcriptions
- ✅ Normalise les fichiers audio

```bash
python scripts/prepare_jsut_dataset.py \
  --jsut-dir dataset/jsut/basic5000 \
  --output-dir dataset/prepared \
  --sample-rate 22050
```

**Durée** : ~30-60 minutes (5,000 fichiers audio)

**Résultat dans `dataset/prepared/`** :
```
dataset/prepared/
├── wav/                    # Audio normalisé (22050 Hz)
│   ├── BASIC5000_0001.wav
│   ├── BASIC5000_0002.wav
│   └── ...
└── metadata.csv            # Format: audio_file|transcription_japonaise
```

**Exemple `metadata.csv`** :
```csv
BASIC5000_0001.wav|人間は、自然を征服しようとしてきた。
BASIC5000_0002.wav|今日は良い天気ですね。
BASIC5000_0003.wav|ありがとうございます。
```

## Étape 3 : Phonétiser le corpus

Cette étape convertit le japonais en phonèmes :
- Kanji → Hiragana (avec pykakasi)
- Hiragana → Phoneme IDs (mapping custom)

```bash
python scripts/phonemize_japanese.py \
  --input dataset/prepared/metadata.csv \
  --output dataset/prepared/metadata_phonemes.csv \
  --phoneme-map dataset/prepared/phoneme_map.json
```

**Durée** : ~3-5 minutes

**Résultat** :
- `metadata_phonemes.csv` : `audio_file|0 1 2 3 4 5 ...` (phoneme IDs)
- `phoneme_map.json` : Mapping hiragana → phoneme IDs (~100 phonèmes)

**Exemple `metadata_phonemes.csv`** :
```csv
BASIC5000_0001.wav|45 12 67 32 89 12 ...
BASIC5000_0002.wav|23 45 12 78 90 34 ...
```

## Étape 4 : Préprocesser pour Piper

Cette étape crée les fichiers de training :
- `dataset.jsonl` : Format Piper (JSON lines)
- `config.json` : Configuration avec phonemes japonais
- `audio_norm_stats.json` : Statistiques normalisation

```bash
python scripts/preprocess_piper.py \
  --input-metadata dataset/prepared/metadata_phonemes.csv \
  --phoneme-map dataset/prepared/phoneme_map.json \
  --audio-dir dataset/prepared/wav \
  --output-dir training \
  --sample-rate 22050
```

**Durée** : ~5-10 minutes

**Résultat dans `training/`** :
```
training/
├── dataset.jsonl            # {"audio_file": "...", "phoneme_ids": [0,1,2,...]}
├── config.json              # Config Piper avec phonemes japonais custom
└── audio_norm_stats.json    # Stats normalisation audio
```

## Étape 5 : Télécharger un checkpoint de base (optionnel mais recommandé)

Le **transfer learning** accélère l'entraînement de **10-50x** !

```bash
mkdir -p checkpoints

# Option A : Checkpoint multi-langue Piper (si disponible)
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/base_model.ckpt \
  -O checkpoints/base_model.ckpt

# Option B : Checkpoint japonais pré-entraîné (si disponible)
# Vérifier : https://github.com/rhasspy/piper/releases
```

> ⚠️ **Note** : Si aucun checkpoint disponible, le système entraînera from scratch (beaucoup plus long).

## Étape 6 : Entraîner le modèle

### Option A : Training rapide (expérimentation)

Pour tester rapidement (100 epochs) :

```bash
python scripts/train_voice.py \
  --dataset-dir training \
  --output-dir output \
  --checkpoint-dir checkpoints \
  --fast-experiment
```

**Durée** : ~30 minutes à 2 heures (selon hardware)
- GPU NVIDIA : ~30-60 minutes
- Apple Silicon (M1/M2/M3) : ~1-2 heures
- CPU : ~5-10 heures

### Option B : Training haute qualité (production)

Pour un modèle de production (5000 epochs) :

```bash
python scripts/train_voice.py \
  --dataset-dir training \
  --output-dir output \
  --checkpoint-dir checkpoints \
  --high-quality
```

**Durée** : 1-3 jours (selon hardware et dataset)
- GPU NVIDIA : ~1-2 jours
- Apple Silicon : ~2-3 jours
- CPU : non recommandé (trop long)

### Option C : Training custom

```bash
python scripts/train_voice.py \
  --dataset-dir training \
  --output-dir output \
  --checkpoint-dir checkpoints \
  --batch-size 32 \
  --learning-rate 1e-4 \
  --max-epochs 1000 \
  --accelerator gpu  # ou mps (Apple Silicon) ou cpu
```

**Pendant l'entraînement** :
- Les logs s'affichent en temps réel avec epoch/loss
- Les checkpoints sont sauvegardés dans `checkpoints/` tous les 50 epochs
- Vous pouvez interrompre (Ctrl+C) et reprendre plus tard automatiquement

**Monitoring avec TensorBoard** :
```bash
# Dans un autre terminal
tensorboard --logdir lightning_logs
# Ouvrir http://localhost:6006
```

## Étape 7 : Exporter le modèle ONNX

Une fois l'entraînement terminé :

```bash
# Lister les checkpoints disponibles
ls -lh checkpoints/

# Exporter le meilleur checkpoint
python -m piper_train.export_onnx \
  checkpoints/epoch-999-step-50000.ckpt \
  models/voice_ja_jsut.onnx

# Copier la configuration
cp training/config.json models/voice_ja_jsut.onnx.json
```

**Résultat** :
```
models/
├── voice_ja_jsut.onnx        # Modèle ONNX (~60-100 MB)
└── voice_ja_jsut.onnx.json   # Configuration
```

## Étape 8 : Tester votre voix !

```bash
# Test simple
echo 'こんにちは、これは私のカスタム音声です。' | \
  piper --model models/voice_ja_jsut.onnx \
       --output_file test_output.wav

# Écouter le résultat
afplay test_output.wav  # macOS
# ou
aplay test_output.wav   # Linux
```

## Workflow Complet (Copy-Paste)

```bash
# 1. Télécharger JSUT
./scripts/download_jsut.sh

# 2. Préparer dataset
python scripts/prepare_jsut_dataset.py \
  --jsut-dir dataset/jsut/basic5000 \
  --output-dir dataset/prepared \
  --sample-rate 22050

# 3. Phonétiser
python scripts/phonemize_japanese.py \
  --input dataset/prepared/metadata.csv \
  --output dataset/prepared/metadata_phonemes.csv \
  --phoneme-map dataset/prepared/phoneme_map.json

# 4. Préprocesser pour Piper
python scripts/preprocess_piper.py \
  --input-metadata dataset/prepared/metadata_phonemes.csv \
  --phoneme-map dataset/prepared/phoneme_map.json \
  --audio-dir dataset/prepared/wav \
  --output-dir training \
  --sample-rate 22050

# 5. Télécharger checkpoint de base (optionnel)
mkdir -p checkpoints
# wget <checkpoint_url> -O checkpoints/base_model.ckpt

# 6. Entraîner (fast experiment)
python scripts/train_voice.py \
  --dataset-dir training \
  --output-dir output \
  --checkpoint-dir checkpoints \
  --fast-experiment

# 7. Exporter ONNX
python -m piper_train.export_onnx \
  checkpoints/epoch-99-step-*.ckpt \
  models/voice_ja_jsut.onnx

cp training/config.json models/voice_ja_jsut.onnx.json

# 8. Tester
echo 'テストメッセージです。' | \
  piper --model models/voice_ja_jsut.onnx \
       --output_file test.wav

afplay test.wav
```

## Durées Estimées

| Étape | Durée (GPU) | Durée (Apple Silicon) | Durée (CPU) |
|-------|-------------|----------------------|-------------|
| 1. Télécharger JSUT | ~10 min | ~10 min | ~10 min |
| 2. Préparer dataset | ~30 min | ~45 min | ~1h |
| 3. Phonétiser | ~3 min | ~5 min | ~10 min |
| 4. Préprocesser | ~5 min | ~8 min | ~15 min |
| 5. Training (fast) | ~30 min | ~1-2h | ~5-10h |
| 5. Training (high quality) | ~1-2 jours | ~2-3 jours | Non recommandé |
| 6. Export ONNX | ~1 min | ~1 min | ~1 min |

**Total (fast experiment)** : ~1-2 heures avec GPU

## Qualité Attendue

**Avec basic5000 (5,000 phrases)** :
- Fast experiment (100 epochs) : Qualité acceptable, compréhensible
- Standard (1000 epochs) : Bonne qualité, naturel
- High quality (5000 epochs) : Très bonne qualité, proche naturel

**Pour améliorer la qualité** :
- Utiliser plus de données (onomatopoeic5000, voiceactress100)
- Entraîner plus longtemps (5000-10000 epochs)
- Utiliser un meilleur checkpoint de base

## Dépannage

### Erreur : "JSUT directory not found"
```bash
# Vérifier le chemin
ls dataset/jsut/basic5000/wav

# Re-télécharger si nécessaire
./scripts/download_jsut.sh
```

### Erreur : "PyTorch not available"
```bash
# Installer PyTorch
pip install torch torchvision torchaudio

# Ou avec GPU CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Training très lent
- Vérifier hardware détecté : logs affichent "Detected CUDA GPU" / "Detected Apple Silicon (MPS)" / "Using CPU"
- Si CPU détecté alors que GPU disponible : installer PyTorch avec support GPU
- Réduire batch size si out of memory : `--batch-size 16` ou `--batch-size 8`

### Out of Memory (OOM)
```bash
# Réduire batch size
python scripts/train_voice.py ... --batch-size 16  # ou 8
```

## Citation

Si vous utilisez JSUT, merci de citer :

```
Ryosuke Sonobe, Shinnosuke Takamichi and Hiroshi Saruwatari,
"JSUT corpus: free large-scale Japanese speech corpus for end-to-end speech synthesis,"
arXiv preprint, 1711.00354, 2017.
```

## Ressources

- **JSUT Dataset** : https://sites.google.com/site/shinnosuketakamichi/publication/jsut
- **Piper TTS** : https://github.com/rhasspy/piper
- **Documentation Piper** : https://github.com/rhasspy/piper/blob/master/TRAINING.md
