# Windows/WSL Setup Guide

Ce guide explique comment configurer le projet sur Windows avec WSL (Windows Subsystem for Linux).

## Prérequis

- Windows 10/11 avec WSL2 installé
- Ubuntu 22.04 LTS (ou version compatible) dans WSL
- Git installé dans WSL

## Installation complète

### 1. Cloner le repo avec les submodules

```bash
# Clone avec les submodules (IMPORTANT!)
git clone --recursive https://github.com/YOUR_USERNAME/jpa_voice_piper.git
cd jpa_voice_piper

# Ou si vous avez déjà cloné sans --recursive:
git submodule update --init --recursive
```

⚠️ **IMPORTANT**: Le flag `--recursive` est obligatoire pour récupérer le sous-module `piper-training/` qui contient le code de Piper TTS.

### 2. Installer les dépendances système

```bash
# Mise à jour des paquets
sudo apt update && sudo apt upgrade -y

# Installer les dépendances Python et audio
sudo apt install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    espeak-ng \
    wget \
    unzip \
    git-lfs

# Activer Git LFS
git lfs install
```

### 3. Installer UV (gestionnaire de packages Python)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Recharger le shell
source ~/.bashrc  # ou source ~/.zshrc selon votre shell
```

### 4. Installer les dépendances Python du projet

```bash
# Sync des dépendances principales
uv sync

# Sync avec les extras audio (obligatoire pour le traitement audio)
uv sync --extra audio

# Sync avec les extras training (obligatoire pour le training Piper)
uv sync --extra training
```

### 5. Vérifier l'installation

```bash
# Vérifier espeak-ng
espeak-ng --voices | grep ja

# Vérifier que piper_train est accessible
uv run python -c "import piper_train; print(piper_train.__file__)"

# Lancer les tests
./scripts/test.sh
```

## Problèmes courants

### Erreur: `piper_train` module not found

**Symptôme**: Le script `create_japanese_voice.sh` échoue avec:
```
ModuleNotFoundError: No module named 'piper_train'
```

**Solution**:
```bash
# 1. Vérifier que le submodule est bien présent
ls -la piper-training/

# Si vide ou absent:
git submodule update --init --recursive

# 2. Installer piper_train en mode développement
cd piper-training
uv pip install -e .
cd ..

# 3. Vérifier l'installation
uv run python -c "import piper_train; print('✅ piper_train OK')"
```

### Erreur: `espeak-ng` voices not found

**Symptôme**:
```
Error: espeak-ng voices not installed
```

**Solution**:
```bash
# Installer les voix espeak-ng
sudo apt install -y espeak-ng espeak-ng-data

# Vérifier que la voix japonaise est disponible
espeak-ng --voices | grep ja
```

### Erreur: Permission denied sur les scripts

**Symptôme**:
```
bash: ./scripts/create_japanese_voice.sh: Permission denied
```

**Solution**:
```bash
# Rendre les scripts exécutables
chmod +x scripts/*.sh

# Ou exécuter avec bash explicitement
bash scripts/create_japanese_voice.sh
```

### Erreur: Git LFS files not downloaded

**Symptôme**: Les fichiers audio dans `dataset/prepared/` sont des pointeurs Git LFS au lieu de vrais fichiers.

**Solution**:
```bash
# Installer Git LFS
sudo apt install git-lfs
git lfs install

# Télécharger les fichiers LFS
git lfs pull
```

## Workflow de développement sur WSL

### Accéder aux fichiers depuis Windows

Les fichiers WSL sont accessibles depuis Windows Explorer à:
```
\\wsl$\Ubuntu\home\YOUR_USERNAME\jpa_voice_piper
```

### Éditer le code

Vous pouvez éditer le code avec:
- VS Code avec l'extension "Remote - WSL"
- JetBrains IDE avec le support WSL
- Éditeur dans WSL (vim, nano, etc.)

### Exécuter les commandes

Toujours exécuter les commandes **dans WSL**, pas dans PowerShell Windows:

```bash
# ✅ CORRECT (dans WSL)
cd ~/jpa_voice_piper
./scripts/create_japanese_voice.sh

# ❌ INCORRECT (dans PowerShell Windows)
# Ne fonctionnera pas correctement
```

## Performance sur WSL

### GPU/CUDA (optionnel)

Pour utiliser le GPU Nvidia avec PyTorch dans WSL:

```bash
# Vérifier support CUDA
nvidia-smi

# Si disponible, PyTorch détectera automatiquement le GPU
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Apple Silicon (M1/M2/M3)

Si vous utilisez un Mac avec Apple Silicon:

```bash
# PyTorch utilisera automatiquement Metal Performance Shaders (MPS)
uv run python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

## Aide supplémentaire

Pour plus d'informations:
- Documentation principale: `README.md`
- Règles du projet: `CLAUDE.md`
- Guide de training: `docs/TRAINING.md`
- Guide utilisateur: `docs/USER_GUIDE.md`

Pour signaler un problème:
```bash
# Vérifier les logs
cat logs/training_*.log
cat logs/quality_*.json

# Créer une issue sur GitHub avec:
# - Votre configuration système (uname -a)
# - Version Python (python3 --version)
# - Sortie complète de l'erreur
```
