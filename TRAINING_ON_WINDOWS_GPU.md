# Guide : Training sur Windows avec GPU NVIDIA

Ce guide vous explique comment transférer le projet depuis votre Mac vers un PC Windows avec GPU NVIDIA pour accélérer le training.

---

## 🎯 Vue d'ensemble

**Ce qui est portable** :
- ✅ Dataset préparé (`dataset/prepared/`)
- ✅ Scripts de training (Python cross-platform)
- ✅ Configuration Piper (hiragana-as-phonemes)

**Ce qui est spécifique à macOS** :
- ❌ MPS (Apple Silicon accelerator)
- ❌ Certains chemins système

**Adaptations nécessaires** :
- ✅ Installer CUDA + PyTorch GPU sur Windows
- ✅ Changer `--trainer.accelerator mps` → `gpu`
- ✅ Ajuster `num_workers` (0 sur Mac → 4 sur Windows)

---

## 📦 Étape 1 : Préparer le transfert depuis Mac

### 1.1 Créer une archive du projet

```bash
# Sur votre Mac
cd ~/Projects/jpa_voice_piper

# Créer archive (exclure fichiers lourds temporaires)
tar -czf jpa_voice_piper_dataset.tar.gz \
  dataset/prepared/ \
  scripts/ \
  piper_voice/ \
  tests/ \
  pyproject.toml \
  uv.lock \
  README.md \
  CLAUDE.md \
  TRAINING_FAILURE_REPORT.md \
  TRAINING_ON_WINDOWS_GPU.md
```

### 1.2 Transférer l'archive

**Options** :

**A) USB / Disque externe** (recommandé si gros dataset)
```bash
# Copier sur clé USB
cp jpa_voice_piper_dataset.tar.gz /Volumes/USB_DRIVE/
```

**B) Cloud (Google Drive, Dropbox, etc.)**
```bash
# Upload vers cloud de votre choix
# Puis télécharger sur Windows
```

**C) Réseau local (si Mac et PC sur même réseau)**
```bash
# Sur Mac, partager le fichier via HTTP simple
python3 -m http.server 8000

# Sur Windows, télécharger:
# http://<MAC_IP>:8000/jpa_voice_piper_dataset.tar.gz
```

---

## 🖥️ Étape 2 : Installation sur Windows

### 2.1 Vérifier GPU NVIDIA

Ouvrir **PowerShell** ou **Command Prompt** :

```powershell
# Vérifier présence GPU NVIDIA
nvidia-smi
```

**Attendu** : Liste de vos GPUs avec utilisation mémoire

Si erreur → Installer les drivers NVIDIA : https://www.nvidia.com/Download/index.aspx

### 2.2 Installer Python 3.11+

**Option A : Python.org**
- Télécharger depuis https://www.python.org/downloads/
- Cocher "Add Python to PATH" lors de l'installation

**Option B : Anaconda/Miniconda**
```powershell
# Télécharger Miniconda
# https://docs.conda.io/en/latest/miniconda.html

# Créer environnement
conda create -n piper python=3.11
conda activate piper
```

### 2.3 Installer CUDA Toolkit (si pas déjà installé)

**Vérifier version CUDA supportée** :
```powershell
nvidia-smi
# Regarder ligne "CUDA Version: X.X"
```

**Installer CUDA Toolkit** :
- Télécharger depuis https://developer.nvidia.com/cuda-downloads
- Version recommandée : **CUDA 11.8** ou **12.1** (compatibilité PyTorch)

### 2.4 Extraire le projet

```powershell
# Naviguer vers répertoire de travail
cd C:\Users\VotreNom\Projects

# Extraire archive (nécessite 7-Zip ou similaire)
tar -xzf jpa_voice_piper_dataset.tar.gz
cd jpa_voice_piper
```

### 2.5 Installer dépendances Python

**Option A : Avec uv (recommandé)**
```powershell
# Installer uv
pip install uv

# Installer dépendances
uv sync --extra training --extra audio
```

**Option B : Avec pip classique**
```powershell
# Installer PyTorch avec support CUDA
# Vérifier version CUDA installée et adapter commande
# Pour CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Pour CUDA 12.1:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installer Piper Training
pip install piper-tts[training]

# Installer autres dépendances
pip install soundfile librosa numpy pykakasi
```

### 2.6 Vérifier installation PyTorch GPU

```powershell
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Attendu** :
```
CUDA available: True
GPU count: 1 (ou plus)
GPU name: NVIDIA GeForce RTX 3080 (exemple)
```

Si `CUDA available: False` → Réinstaller PyTorch avec bonne version CUDA

---

## 🚀 Étape 3 : Lancer le training

### 3.1 Vérifier le dataset

```powershell
# Compter samples
python -c "with open('dataset/prepared/metadata_phonemes.csv') as f: print(f'Samples: {sum(1 for _ in f)}')"

# Vérifier phoneme_map
python -c "import json; data = json.load(open('dataset/prepared/phoneme_map.json')); print(f'Phonemes: {len(data[\"phonemes\"])}')"
```

**Attendu** :
```
Samples: 4061
Phonemes: 86
```

### 3.2 Lancer le training (méthode simple)

```powershell
# Lancer avec auto-détection GPU
python scripts/train_japanese_voice.py
```

Le script va :
1. ✅ Détecter automatiquement le GPU NVIDIA
2. ✅ Télécharger checkpoint français (transfer learning)
3. ✅ Configurer `batch_size=32`, `num_workers=4`
4. ✅ Lancer training 200 epochs

### 3.3 Lancer le training (méthode manuelle)

Si vous préférez contrôler tous les paramètres :

```powershell
# Télécharger checkpoint français
mkdir checkpoints
curl -L -o checkpoints/fr_FR-siwis-medium.ckpt https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt

# Lancer training
python -m piper.train fit ^
  --data.voice_name "ja_JP-jsut-medium" ^
  --data.csv_path "dataset/prepared/metadata_phonemes.csv" ^
  --data.audio_dir "dataset/prepared/wav" ^
  --data.cache_dir "training" ^
  --data.config_path "training/config.json" ^
  --data.batch_size 32 ^
  --data.validation_split 0.1 ^
  --data.num_workers 4 ^
  --data.phoneme_type "text" ^
  --data.espeak_voice "ja" ^
  --model.sample_rate 22050 ^
  --model.learning_rate 0.00005 ^
  --trainer.max_epochs 200 ^
  --trainer.check_val_every_n_epoch 5 ^
  --trainer.accelerator "gpu" ^
  --trainer.precision 32 ^
  --ckpt_path "checkpoints/fr_FR-siwis-medium.ckpt"
```

**Note** : Sur Windows, utiliser `^` pour continuer sur nouvelle ligne (au lieu de `\` sur Mac/Linux)

### 3.4 Monitoring avec TensorBoard

**Ouvrir un nouveau terminal PowerShell** :

```powershell
cd C:\Users\VotreNom\Projects\jpa_voice_piper

# Lancer TensorBoard
tensorboard --logdir lightning_logs --port 6006
```

**Ouvrir dans navigateur** : http://localhost:6006

**Métriques importantes à surveiller** :
- `loss_g` (Generator loss) : doit descendre < 5.0
- `val_loss` (Validation loss) : doit descendre < 10.0 et NE PAS augmenter
- `loss_d` (Discriminator loss) : doit rester stable autour de 1.0-2.0

**Courbes attendues** :
```
loss_g:   34 → 25 → 15 → 8 → 5 → 3 → 2   ✅ Bon
val_loss: 32 → 20 → 12 → 8 → 6 → 5 → 4   ✅ Bon
```

**Courbes problématiques** :
```
loss_g:   34 → 32 → 30 → 29 → 28 → 28    ❌ Pas de convergence
val_loss: 32 → 20 → 15 → 18 → 25 → 33    ❌ Overfitting
```

---

## ⏱️ Durée estimée

**Avec GPU NVIDIA (RTX 3060 ou supérieur)** :
- Transfer learning (200 epochs) : **6-12 heures**
- From scratch (500 epochs) : **24-48 heures**

**Optimisations possibles** :
- RTX 4090 : ~3-4h (transfer learning)
- Multi-GPU : diviser par nombre de GPUs
- Mixed precision (FP16) : +30% vitesse (mais peut être instable)

---

## 🔍 Troubleshooting

### Problème 1 : `RuntimeError: CUDA out of memory`

**Cause** : Batch size trop grand pour GPU

**Solution** :
```powershell
# Réduire batch size
python scripts/train_japanese_voice.py  # Modifier batch_size dans script
# OU
python -m piper.train fit --data.batch_size 16 ...  # Au lieu de 32
```

### Problème 2 : `CUDA available: False`

**Cause** : PyTorch installé sans support CUDA

**Solution** :
```powershell
# Désinstaller PyTorch
pip uninstall torch torchvision torchaudio

# Réinstaller avec CUDA (adapter version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Problème 3 : Training très lent malgré GPU

**Cause** : `num_workers=0` ou batch size trop petit

**Solution** :
```powershell
# Augmenter num_workers (4-8 selon CPU)
# Augmenter batch_size (32-64 selon mémoire GPU)
```

### Problème 4 : Loss ne descend pas

**Causes possibles** :
1. Dataset mal préparé
2. Learning rate trop élevé
3. Batch size trop petit

**Vérifications** :
```powershell
# Vérifier dataset
python -c "import json; with open('training/dataset.jsonl') as f: data = [json.loads(line) for line in f]; print(f'Dataset samples: {len(data)}'); print(f'Sample: {data[0]}')"

# Vérifier premier sample audio existe
python -c "from pathlib import Path; p = Path('dataset/prepared/wav/BASIC5000_0001.wav'); print(f'Audio exists: {p.exists()}, Size: {p.stat().st_size if p.exists() else 0} bytes')"
```

---

## 📊 Après le training

### 1. Trouver le meilleur checkpoint

```powershell
# Lister checkpoints
dir lightning_logs\version_*\checkpoints\*.ckpt

# Choisir celui avec loss la plus basse (epoch le plus élevé)
# Exemple: epoch=199-step=182800.ckpt
```

### 2. Exporter vers ONNX

```powershell
python -m piper.train.export_onnx ^
  lightning_logs\version_0\checkpoints\epoch=199-step=182800.ckpt ^
  models\ja_JP-jsut-medium.onnx

# Copier config
copy training\config.json models\ja_JP-jsut-medium.onnx.json
```

### 3. Tester la voix

**Option A : Avec Piper CLI**
```powershell
# Installer Piper
pip install piper-tts

# Tester
echo こんにちは | piper -m models\ja_JP-jsut-medium.onnx -f test.wav

# Écouter (avec lecteur audio Windows)
start test.wav
```

**Option B : Avec script Python**
```powershell
python test_model_correct.py
```

### 4. Transférer le modèle vers Mac (optionnel)

```powershell
# Créer archive du modèle
tar -czf trained_model.tar.gz models\ lightning_logs\version_0\

# Transférer vers Mac (USB, cloud, réseau)
```

---

## 🎯 Checklist complète

**Avant de commencer** :
- [ ] GPU NVIDIA détecté (`nvidia-smi`)
- [ ] CUDA installé (version 11.8 ou 12.1)
- [ ] Python 3.11+ installé
- [ ] PyTorch GPU installé (`torch.cuda.is_available() == True`)
- [ ] Dataset extrait (4061 samples dans `dataset/prepared/`)
- [ ] Scripts de training présents

**Pendant le training** :
- [ ] TensorBoard lancé (http://localhost:6006)
- [ ] `loss_g` descend progressivement
- [ ] `val_loss` descend progressivement
- [ ] Pas d'erreur CUDA OOM
- [ ] GPU utilisé à > 80% (`nvidia-smi` toutes les 10 min)

**Après le training** :
- [ ] `loss_g < 5.0` atteint
- [ ] `val_loss < 10.0` atteint
- [ ] Checkpoint exporté vers ONNX
- [ ] Audio généré testé et compréhensible
- [ ] Documentation mise à jour

---

## 📚 Ressources

**CUDA et PyTorch** :
- CUDA Toolkit : https://developer.nvidia.com/cuda-downloads
- PyTorch Installation : https://pytorch.org/get-started/locally/

**Piper TTS** :
- Documentation : https://github.com/rhasspy/piper
- Training guide : https://github.com/rhasspy/piper/blob/master/TRAINING.md

**Dataset** :
- JSUT Corpus : https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut-corpus

---

## 💡 Tips pour optimiser

**Performance GPU** :
1. Utiliser `batch_size` le plus grand possible (jusqu'à limite mémoire)
2. Activer `torch.backends.cudnn.benchmark = True`
3. Utiliser `num_workers = 4-8` (selon nombre de CPU cores)
4. Éviter `precision=16` si instable (rester en `precision=32`)

**Qualité du modèle** :
1. Transfer learning TOUJOURS meilleur que from-scratch
2. Minimum 200 epochs pour convergence
3. Vérifier `val_loss` ne diverge pas (early stopping si besoin)
4. Comparer audio généré tous les 20-30 epochs

**Économiser du temps** :
1. Commencer avec 50 epochs test pour valider setup
2. Si `loss_g` descend bien → Lancer training complet
3. Si `loss_g` stagne → Vérifier dataset et hyperparams

---

**Bonne chance avec le training ! 🚀**
