# Package de Transfert - Training Voix Japonaise

Ce package contient tout le nécessaire pour entraîner la voix japonaise Piper TTS sur un autre ordinateur.

---

## 📦 Contenu du Package

```
jpa_voice_piper/
├── dataset/prepared/          # Dataset préparé (4061 samples)
│   ├── metadata_phonemes.csv  # Transcriptions + phonèmes
│   ├── phoneme_map.json       # Mapping hiragana → IDs
│   └── wav/                   # Fichiers audio (22050 Hz)
│
├── scripts/                   # Scripts de training
│   ├── train_japanese_voice.py      # Training cross-platform
│   ├── train_japanese_voice.sh      # Training bash (Mac/Linux)
│   └── validate_environment.py      # Validation environnement
│
├── piper_voice/               # Code projet (architecture DDD)
├── tests/                     # Tests unitaires
├── pyproject.toml            # Dépendances Python
├── TRAINING_ON_WINDOWS_GPU.md       # Guide complet Windows
├── TRAINING_FAILURE_REPORT.md       # Analyse du problème
└── SUMMARY_AND_NEXT_STEPS.md        # Résumé et actions
```

**Taille totale** : ~2-3 GB (principalement audio)

---

## 🚀 Démarrage Rapide

### Sur Windows avec GPU NVIDIA

```powershell
# 1. Extraire le package
cd C:\Users\VotreNom\Projects
tar -xzf jpa_voice_piper_dataset.tar.gz
cd jpa_voice_piper

# 2. Installer PyTorch GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. Installer Piper Training
pip install piper-tts[training]

# 4. Valider environnement
python scripts/validate_environment.py

# 5. Lancer training
python scripts/train_japanese_voice.py
```

**Durée estimée** : 6-12 heures

---

### Sur Mac/Linux

```bash
# 1. Extraire le package
cd ~/Projects
tar -xzf jpa_voice_piper_dataset.tar.gz
cd jpa_voice_piper

# 2. Installer dépendances
pip install uv
uv sync --extra training --extra audio

# 3. Valider environnement
python scripts/validate_environment.py

# 4. Lancer training
python scripts/train_japanese_voice.py
```

**Durée estimée** : 12-24 heures (Apple Silicon)

---

## ✅ Validation Avant Training

**TOUJOURS exécuter ceci en premier** :

```bash
python scripts/validate_environment.py
```

Ce script vérifie :
- ✅ Python 3.11+
- ✅ PyTorch installé
- ✅ GPU détecté (CUDA ou MPS)
- ✅ Piper training installé
- ✅ Dataset complet (4061 samples)
- ✅ Espace disque (> 10 GB)

**Si tous les checks passent** → Vous pouvez commencer le training

**Si erreurs** → Voir messages d'erreur et corriger avant de continuer

---

## 📊 Monitoring Pendant le Training

### TensorBoard (recommandé)

```bash
# Dans un terminal séparé
tensorboard --logdir ./lightning_logs --port 6006

# Ouvrir dans navigateur
# http://localhost:6006
```

**Métriques à surveiller** :
- `loss_g` : Doit descendre progressivement (34 → 5 → 2)
- `val_loss` : Doit descendre aussi (pas augmenter !)
- `loss_d` : Doit rester stable autour de 1-2

**Courbes attendues** :
```
Epoch  | loss_g | val_loss
-------|--------|----------
0      | 34.67  | 31.78
50     | 8.45   | 9.12    ← Descend bien ✅
100    | 4.23   | 6.78    ← Continue ✅
150    | 2.56   | 5.34    ← Converge ✅
199    | 1.89   | 4.92    ← SUCCÈS ✅
```

**Courbes problématiques** :
```
Epoch  | loss_g | val_loss
-------|--------|----------
0      | 34.67  | 31.78
50     | 30.23  | 35.67   ← Val loss augmente ❌
100    | 29.76  | 33.00   ← Pas de convergence ❌
```

Si `val_loss` augmente après 50 epochs → **Arrêter et ajuster hyperparamètres**

---

## 🎯 Critères d'Arrêt

**Training réussi** quand :
- ✅ `loss_g < 5.0`
- ✅ `val_loss < 10.0`
- ✅ `val_loss` ne diverge pas
- ✅ Audio généré compréhensible

**Test audio à faire régulièrement** :
```bash
# Export checkpoint temporaire
python -m piper.train.export_onnx \
  lightning_logs/version_0/checkpoints/epoch=50-step=45700.ckpt \
  test_model.onnx

# Test
echo 'こんにちは' | piper -m test_model.onnx -f test.wav

# Écouter
afplay test.wav  # Mac
start test.wav   # Windows
```

---

## 🔧 Troubleshooting

### Erreur : "CUDA out of memory"

**Solution** : Réduire `batch_size`

```bash
# Éditer scripts/train_japanese_voice.py
# Ligne ~140 : batch_size = 32
# Changer à : batch_size = 16
```

### Erreur : "CUDA available: False"

**Cause** : PyTorch sans support GPU

**Solution** :
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Training très lent

**Vérifier GPU utilisé** :
```bash
# NVIDIA GPU
nvidia-smi  # Doit montrer utilisation > 80%

# Apple Silicon
# Regarder Activity Monitor → GPU History
```

### Loss ne descend pas

**Vérifier dataset** :
```bash
python -c "with open('dataset/prepared/metadata_phonemes.csv') as f: print(sum(1 for _ in f))"
# Doit afficher: 4061
```

**Si problème persiste** → Voir `TRAINING_FAILURE_REPORT.md`

---

## 📁 Structure des Outputs

Pendant le training, ces dossiers sont créés :

```
lightning_logs/
└── version_0/
    ├── checkpoints/
    │   ├── epoch=49-step=45700.ckpt
    │   ├── epoch=99-step=91400.ckpt
    │   └── epoch=199-step=182800.ckpt  ← Le meilleur
    ├── config.yaml
    ├── hparams.yaml
    └── events.out.tfevents.*  ← Logs TensorBoard
```

**Taille** : ~800 MB par checkpoint

---

## 🎉 Après le Training

### 1. Trouver meilleur checkpoint

```bash
ls -lh lightning_logs/version_0/checkpoints/*.ckpt
```

Choisir le dernier (epoch le plus élevé avec `loss_g` le plus bas)

### 2. Exporter vers ONNX

```bash
python -m piper.train.export_onnx \
  lightning_logs/version_0/checkpoints/epoch=199-step=182800.ckpt \
  models/ja_JP-jsut-medium.onnx

# Copier config
cp training/config.json models/ja_JP-jsut-medium.onnx.json
```

### 3. Tester la voix

```bash
# Test simple
echo 'こんにちは' | piper -m models/ja_JP-jsut-medium.onnx -f test.wav

# Écouter
afplay test.wav  # Mac
start test.wav   # Windows

# Test phrases plus longues
python test_model_correct.py
```

### 4. Transférer le modèle

**Si entraîné sur Windows, retour vers Mac** :

```powershell
# Sur Windows - Créer archive
tar -czf trained_model.tar.gz models/ lightning_logs/version_0/

# Transférer via USB/Cloud

# Sur Mac - Extraire
tar -xzf trained_model.tar.gz
```

---

## 📚 Documentation Complète

**Avant de commencer** :
1. `SUMMARY_AND_NEXT_STEPS.md` - Vue d'ensemble
2. `scripts/validate_environment.py` - Validation environnement

**Pendant le training** :
1. TensorBoard → http://localhost:6006
2. `TRAINING_ON_WINDOWS_GPU.md` - Guide Windows

**Si problèmes** :
1. `TRAINING_FAILURE_REPORT.md` - Diagnostic technique
2. Section Troubleshooting ci-dessus

---

## ⏱️ Estimations Durée

| Hardware            | Transfer Learning | From Scratch |
|---------------------|-------------------|--------------|
| RTX 4090            | 3-4h              | 12-16h       |
| RTX 3080/3090       | 6-8h              | 24-32h       |
| RTX 3060            | 10-12h            | 40-48h       |
| Apple M1/M2 Max     | 12-24h            | 48-96h       |
| CPU (non recommandé)| 3-7 jours         | 10-14 jours  |

**Note** : Ces durées sont pour 200 epochs (transfer learning) ou 500 epochs (from scratch)

---

## ✅ Checklist Complète

**Installation** :
- [ ] Package extrait
- [ ] Python 3.11+ installé
- [ ] PyTorch GPU installé
- [ ] Piper training installé
- [ ] `validate_environment.py` passe tous les checks

**Avant training** :
- [ ] GPU détecté (`nvidia-smi` ou MPS)
- [ ] Dataset validé (4061 samples)
- [ ] TensorBoard prêt
- [ ] Espace disque > 10 GB

**Pendant training** :
- [ ] TensorBoard accessible (http://localhost:6006)
- [ ] `loss_g` descend progressivement
- [ ] `val_loss` descend (ne diverge pas)
- [ ] GPU utilisé > 80%

**Après training** :
- [ ] `loss_g < 5.0` atteint
- [ ] `val_loss < 10.0` atteint
- [ ] Modèle exporté ONNX
- [ ] Audio test compréhensible
- [ ] Documentation mise à jour

---

## 📞 Support

**Si vous rencontrez des problèmes** :

1. Vérifier `validate_environment.py`
2. Lire `TRAINING_ON_WINDOWS_GPU.md` (section Troubleshooting)
3. Consulter `TRAINING_FAILURE_REPORT.md` (analyse technique)
4. Vérifier logs TensorBoard

**Informations utiles à fournir** :
- Sortie de `python scripts/validate_environment.py`
- GPU utilisé (`nvidia-smi`)
- Screenshot TensorBoard (courbes losses)
- Messages d'erreur complets

---

**Bonne chance avec le training ! 🚀**

N'oubliez pas de monitorer régulièrement avec TensorBoard et de tester l'audio tous les 50 epochs environ.
