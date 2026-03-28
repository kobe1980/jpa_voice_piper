# Guide de Démarrage Rapide - Windows

Ce guide vous permet de lancer le training sur Windows en quelques minutes.

---

## 🚀 Démarrage Ultra-Rapide

```powershell
# 1. Cloner le repo (avec Git LFS pour le dataset)
git clone https://github.com/kobe1980/jpa_voice_piper.git
cd jpa_voice_piper

# 2. Setup complet (Python, PyTorch GPU, Piper, validation)
setup_windows.bat

# 3. Lancer le training
train_windows.bat
```

**C'est tout !** Le dataset (4061 samples, 5.4 GB) est inclus via Git LFS.

---

## 📋 Prérequis

### Obligatoire
- ✅ **Windows 10/11** (64-bit)
- ✅ **Python 3.11+** ([Télécharger](https://www.python.org/downloads/))
- ✅ **Git avec Git LFS** ([Télécharger](https://git-scm.com/downloads))

### Recommandé pour vitesse
- ✅ **GPU NVIDIA** (RTX 2060 ou supérieur)
- ✅ **Drivers NVIDIA** à jour ([Télécharger](https://www.nvidia.com/Download/index.aspx))
- ✅ **16 GB RAM** minimum (32 GB recommandé)
- ✅ **50 GB espace disque** libre

### Sans GPU
⚠️ Le training sur CPU est **TRÈS LENT** (3-7 jours vs 6-12h sur GPU)

---

## 🔧 Installation Détaillée

### Étape 1 : Installer Git avec Git LFS

**Télécharger Git** : https://git-scm.com/downloads

Lors de l'installation :
- ✅ Cocher "Git LFS" (Large File Support)
- ✅ Cocher "Add to PATH"

**Vérifier** :
```powershell
git --version
git lfs version
```

### Étape 2 : Installer Python

**Télécharger Python 3.11+** : https://www.python.org/downloads/

Lors de l'installation :
- ✅ **IMPORTANT** : Cocher "Add Python to PATH"
- ✅ Choisir "Install for all users" (optionnel)

**Vérifier** :
```powershell
python --version
# Doit afficher: Python 3.11.x ou supérieur
```

### Étape 3 : Installer Drivers NVIDIA (si GPU)

**Vérifier GPU** :
```powershell
nvidia-smi
```

Si erreur → Installer drivers : https://www.nvidia.com/Download/index.aspx

**Choisir** :
- Product Type : GeForce / Quadro / RTX
- Product Series : Votre série (ex: RTX 40 Series)
- Operating System : Windows 11 / 10

---

## 📦 Clonage du Repo

```powershell
# Cloner avec Git LFS (télécharge automatiquement le dataset)
git clone https://github.com/kobe1980/jpa_voice_piper.git
cd jpa_voice_piper
```

**Durée** : 5-15 minutes (selon connexion) pour télécharger 5.4 GB

**Vérifier dataset** :
```powershell
dir dataset\prepared\wav | find /c ".wav"
# Doit afficher: 4061
```

---

## ⚙️ Setup Automatique

Lancer le script de setup :

```powershell
setup_windows.bat
```

**Ce script fait automatiquement** :
1. ✅ Vérifie Python installé
2. ✅ Détecte GPU NVIDIA
3. ✅ Installe PyTorch avec CUDA
4. ✅ Installe Piper Training
5. ✅ Installe dépendances (soundfile, librosa, pykakasi)
6. ✅ Valide le dataset (4061 samples)
7. ✅ Vérifie l'environnement complet

**Choix CUDA** :
- Option 1 : CUDA 11.8 (recommandé, RTX 20/30/40)
- Option 2 : CUDA 12.1 (plus récent, RTX 40)
- Option 3 : CPU seulement (pas recommandé)

**Durée** : 5-10 minutes

---

## 🚀 Lancer le Training

```powershell
train_windows.bat
```

**Le script** :
- ✅ Vérifie que le setup est complet
- ✅ Détecte automatiquement le GPU
- ✅ Télécharge checkpoint français (transfer learning)
- ✅ Lance le training avec hyperparamètres optimisés
- ✅ Affiche progression en temps réel

**Hyperparamètres** :
- `batch_size` : 32
- `learning_rate` : 0.00005
- `max_epochs` : 200
- `accelerator` : gpu (auto-détecté)

**Durée estimée** :
- GPU RTX 4090 : 3-4 heures
- GPU RTX 3080/3090 : 6-8 heures
- GPU RTX 3060 : 10-12 heures
- CPU : **3-7 jours** ⚠️

---

## 📊 Monitoring avec TensorBoard

**Ouvrir un nouveau PowerShell** :

```powershell
cd jpa_voice_piper
tensorboard --logdir lightning_logs --port 6006
```

**Ouvrir dans navigateur** : http://localhost:6006

**Métriques à surveiller** :
- `loss_g` (Generator) : Doit descendre vers < 5.0
- `val_loss` (Validation) : Doit descendre vers < 10.0
- `loss_d` (Discriminator) : Stable autour 1-2

**Bon training** :
```
Epoch   loss_g   val_loss
0       34.67    31.78     ← Départ
50      8.45     9.12      ← Descend
100     4.23     6.78      ← Continue
150     2.56     5.34      ← Converge
199     1.89     4.92      ← Succès ✅
```

**Mauvais training** :
```
Epoch   loss_g   val_loss
0       34.67    31.78
50      30.23    35.67     ← Val loss augmente ❌
```

Si `val_loss` augmente → Arrêter et ajuster hyperparamètres

---

## 🎉 Après le Training

### 1. Trouver le meilleur checkpoint

```powershell
dir lightning_logs\version_0\checkpoints\*.ckpt
```

Choisir le dernier (epoch le plus élevé)

### 2. Exporter vers ONNX

```powershell
python -m piper.train.export_onnx ^
  lightning_logs\version_0\checkpoints\epoch=199-step=182800.ckpt ^
  models\ja_JP-jsut-medium.onnx

copy training\config.json models\ja_JP-jsut-medium.onnx.json
```

### 3. Tester la voix

```powershell
# Installer Piper CLI
pip install piper-tts

# Tester
echo こんにちは | piper -m models\ja_JP-jsut-medium.onnx -f test.wav

# Écouter
start test.wav
```

---

## 🔧 Troubleshooting

### Problème : "git clone" très lent

**Cause** : Dataset 5.4 GB via Git LFS

**Solution** : Attendre (5-15 min selon connexion) ou utiliser meilleure connexion

### Problème : "CUDA out of memory"

**Cause** : GPU n'a pas assez de VRAM

**Solution** : Réduire batch_size dans `scripts\train_japanese_voice.py`
```python
# Ligne ~140
batch_size = 16  # au lieu de 32
```

### Problème : "CUDA available: False"

**Cause** : PyTorch installé sans support CUDA

**Solution** :
```powershell
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Problème : Training très lent malgré GPU

**Vérifier GPU utilisé** :
```powershell
nvidia-smi
# Utilisation GPU doit être > 80%
```

**Solutions** :
- Fermer autres applications utilisant GPU
- Vérifier que le script utilise bien `--accelerator gpu`
- Augmenter `batch_size` si mémoire GPU disponible

### Problème : "Loss ne descend pas"

**Vérifications** :
```powershell
# Vérifier dataset
python -c "with open('dataset/prepared/metadata_phonemes.csv') as f: print(sum(1 for _ in f))"
# Doit afficher: 4061

# Vérifier TensorBoard
tensorboard --logdir lightning_logs
# Regarder courbes loss_g et val_loss
```

**Si stagne après 50 epochs** → Problème hyperparamètres ou dataset

---

## 📚 Documentation Complète

- **TRAINING_ON_WINDOWS_GPU.md** : Guide détaillé Windows
- **TRAINING_FAILURE_REPORT.md** : Analyse du problème initial
- **SUMMARY_AND_NEXT_STEPS.md** : Plan complet
- **CLAUDE.md** : Architecture et règles projet

---

## ✅ Checklist Complète

**Avant de commencer** :
- [ ] Windows 10/11 installé
- [ ] Python 3.11+ installé (dans PATH)
- [ ] Git avec Git LFS installé
- [ ] Drivers NVIDIA à jour (si GPU)
- [ ] 50 GB espace disque libre

**Installation** :
- [ ] `git clone` terminé (5.4 GB)
- [ ] `setup_windows.bat` réussi
- [ ] `python scripts\validate_environment.py` passe

**Pendant training** :
- [ ] TensorBoard accessible (port 6006)
- [ ] GPU utilisé > 80% (`nvidia-smi`)
- [ ] `loss_g` descend progressivement
- [ ] `val_loss` descend (ne diverge pas)

**Après training** :
- [ ] `loss_g < 5.0` atteint
- [ ] `val_loss < 10.0` atteint
- [ ] Modèle exporté ONNX
- [ ] Audio test compréhensible

---

## 💡 Conseils Pro

1. **Premier training** : Commencer avec 50 epochs test pour valider
2. **TensorBoard** : Toujours monitorer, sauver screenshots courbes
3. **Checkpoints** : Sauvegarder plusieurs (au cas où)
4. **Backup** : Copier `lightning_logs/` régulièrement
5. **Test audio** : Tester tous les 20-30 epochs

---

**Bon training ! 🚀**

En cas de problème, voir **TRAINING_ON_WINDOWS_GPU.md** pour troubleshooting détaillé.
