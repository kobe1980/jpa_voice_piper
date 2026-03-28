# Résumé Investigation & Prochaines Étapes

**Date** : 2026-03-28
**Statut** : ✅ **DIAGNOSTIC COMPLET - PRÊT POUR RE-TRAINING**

---

## 🎯 Ce qui a été fait

### 1. Diagnostic du problème ✅

**Symptôme initial** : Audio généré trop court et incompréhensible

**Investigation menée** :
1. ✅ Testé génération avec phonèmes corrects → Fonctionne mais durée trop courte
2. ✅ Comparé durée audio original vs généré → 8x trop rapide (0.37s vs 3.19s)
3. ✅ Testé différents `length_scale` → `length_scale=20.0` donne durée correcte
4. ✅ Écouté audio généré → **Incompréhensible malgré durée correcte**
5. ✅ Analysé losses TensorBoard → **Training n'a PAS convergé**

**Conclusion** : Le modèle actuel est **inutilisable** car training insuffisant

### 2. Analyse des causes ✅

**Losses TensorBoard (epoch 99)** :
```
Generator Loss      : 29.76  (cible: < 5.0)   ❌ 6x trop élevée
Validation Loss     : 33.00  (cible: < 10.0)  ❌ Augmente (overfitting)
Discriminator Loss  : 2.20   (cible: ~1-2)    ✅ OK
```

**Problèmes identifiés** :
1. ❌ `batch_size=8` trop petit (devrait être 32-64)
2. ❌ `max_epochs=100` insuffisant (besoin 200-500)
3. ❌ Pas de transfer learning (training from scratch trop long)

### 3. Validation de l'architecture ✅

**Vérifié que l'approche hiragana-as-phonemes est correcte** :
- ✅ Documentée dans ADR-001 (décision d'architecture acceptée)
- ✅ Supportée officiellement par Piper (`--data.phoneme_type text`)
- ✅ Dataset correctement préparé (4061 samples, 86 phonèmes)
- ✅ Preprocessing Piper réussi (dataset.jsonl généré)

**Rien à changer dans le preprocessing** - Le problème est uniquement le training

### 4. Scripts de training cross-platform créés ✅

**Fichiers créés** :
- `scripts/train_japanese_voice.sh` - Script Bash (macOS/Linux)
- `scripts/train_japanese_voice.py` - Script Python (Windows/macOS/Linux)
- `TRAINING_ON_WINDOWS_GPU.md` - Guide complet transfert Windows + GPU

**Fonctionnalités** :
- ✅ Auto-détection hardware (GPU/MPS/CPU)
- ✅ Download automatique checkpoint français (transfer learning)
- ✅ Hyperparamètres optimisés (batch_size=32, learning_rate=0.00005)
- ✅ Configuration adaptée par plateforme (num_workers)
- ✅ Validation dataset avant lancement
- ✅ Messages clairs et estimations durée

---

## 🚀 Prochaines Étapes

### Option A : Training sur Windows avec GPU NVIDIA (RECOMMANDÉ)

**Avantages** :
- ✅ **Beaucoup plus rapide** (6-12h vs 48-96h sur Mac)
- ✅ Support CUDA mature et optimisé
- ✅ Peut utiliser batch_size plus grand

**Étapes** :
1. Transférer le projet sur Windows (voir `TRAINING_ON_WINDOWS_GPU.md`)
2. Installer CUDA + PyTorch GPU
3. Lancer : `python scripts/train_japanese_voice.py`
4. Monitorer avec TensorBoard
5. Exporter modèle ONNX quand `loss_g < 5.0`

**Durée estimée** : 6-12 heures (avec transfer learning)

---

### Option B : Training sur Mac avec MPS (plus lent)

**Si vous n'avez pas accès à Windows GPU** :

```bash
# Sur votre Mac
cd ~/Projects/jpa_voice_piper

# Lancer training
python scripts/train_japanese_voice.py --accelerator mps

# OU avec script bash
./scripts/train_japanese_voice.sh --accelerator mps
```

**Durée estimée** : 12-24 heures (avec transfer learning)

---

### Option C : Google Colab avec GPU gratuit

**Si vous n'avez ni Windows GPU ni temps d'attendre sur Mac** :

1. Créer notebook Google Colab
2. Activer GPU gratuit (T4)
3. Uploader dataset (`dataset/prepared/`)
4. Installer Piper : `!pip install piper-tts[training]`
5. Lancer training

**Durée estimée** : 8-15 heures (GPU T4)

---

## 📋 Commandes clés

### Lancer le training (auto-détection)

```bash
# Python (recommandé - cross-platform)
python scripts/train_japanese_voice.py

# Bash (macOS/Linux seulement)
./scripts/train_japanese_voice.sh
```

### Forcer un accelerator spécifique

```bash
# Windows avec NVIDIA GPU
python scripts/train_japanese_voice.py --accelerator gpu

# macOS Apple Silicon
python scripts/train_japanese_voice.py --accelerator mps

# CPU (très lent, pas recommandé)
python scripts/train_japanese_voice.py --accelerator cpu
```

### Training from scratch (sans transfer learning)

```bash
# Prend beaucoup plus de temps (200-500 epochs nécessaires)
python scripts/train_japanese_voice.py --from-scratch
```

### Monitorer le training

```bash
# TensorBoard (dans un autre terminal)
tensorboard --logdir ./lightning_logs --port 6006

# Ouvrir : http://localhost:6006
```

### Après training : Export ONNX

```bash
# Trouver meilleur checkpoint
ls -lh lightning_logs/version_*/checkpoints/*.ckpt

# Exporter
python -m piper.train.export_onnx \
  lightning_logs/version_X/checkpoints/epoch=199-step=182800.ckpt \
  models/ja_JP-jsut-medium.onnx

# Copier config
cp training/config.json models/ja_JP-jsut-medium.onnx.json

# Tester
echo 'こんにちは' | piper -m models/ja_JP-jsut-medium.onnx -f test.wav
afplay test.wav
```

---

## 📊 Critères de succès

**Pendant le training**, vérifier sur TensorBoard :

✅ **Bon training** :
```
Epoch  | loss_g | val_loss | Status
-------|--------|----------|--------
0      | 34.67  | 31.78    | Starting
20     | 15.23  | 14.56    | ✅ Descend
50     | 8.45   | 9.12     | ✅ Descend
100    | 4.23   | 6.78     | ✅ Descend
150    | 2.56   | 5.34     | ✅ Converge
199    | 1.89   | 4.92     | ✅ SUCCÈS
```

❌ **Mauvais training** :
```
Epoch  | loss_g | val_loss | Status
-------|--------|----------|--------
0      | 34.67  | 31.78    | Starting
20     | 32.45  | 30.12    | ⚠️ Stagne
50     | 30.23  | 35.67    | ❌ Val loss augmente
100    | 29.76  | 33.00    | ❌ ÉCHEC (cas actuel)
```

**À la fin du training** :
- ✅ `loss_g < 5.0`
- ✅ `val_loss < 10.0`
- ✅ `val_loss` ne diverge pas
- ✅ Audio généré compréhensible

---

## 🔧 Hyperparamètres utilisés

**Configuration optimisée (transfer learning)** :
```python
batch_size = 32              # ← Augmenté de 8 à 32
learning_rate = 0.00005      # ← Réduit pour fine-tuning
max_epochs = 200             # ← Augmenté de 100 à 200
validation_split = 0.1
check_val_every_n_epoch = 5
num_workers = 4              # (0 sur MPS, 4 sur GPU/CPU)
accelerator = "gpu"          # ("mps" sur Mac, "gpu" sur Windows)
precision = 32
```

**Checkpoint de départ** :
```
https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt
```

---

## 📁 Fichiers importants créés

**Documentation** :
- `TRAINING_FAILURE_REPORT.md` - Analyse complète du problème
- `TRAINING_ON_WINDOWS_GPU.md` - Guide transfert Windows + GPU
- `SUMMARY_AND_NEXT_STEPS.md` - Ce document

**Scripts de training** :
- `scripts/train_japanese_voice.sh` - Script Bash (Mac/Linux)
- `scripts/train_japanese_voice.py` - Script Python (cross-platform)

**Scripts de test** :
- `test_model_correct.py` - Test avec vrais phonèmes
- `test_real_dataset_phrases.py` - Test phrases dataset
- `test_with_adjusted_length.py` - Test length_scale

**Diagnostics** :
- `DIAGNOSIS_TRAINING_ISSUE.md` - Première hypothèse (fausse)
- `FINAL_DIAGNOSIS.md` - Diagnostic intermédiaire

---

## ✅ Ce qui est prêt

**Dataset** :
- ✅ 4061 samples JSUT basic5000
- ✅ Audio normalisé 22050 Hz
- ✅ Phonèmes convertis (86 hiraganas)
- ✅ metadata_phonemes.csv généré
- ✅ phoneme_map.json créé
- ✅ dataset.jsonl Piper généré

**Scripts** :
- ✅ Training cross-platform (Windows/Mac/Linux)
- ✅ Auto-détection hardware
- ✅ Transfer learning automatique
- ✅ Hyperparamètres optimisés

**Documentation** :
- ✅ Guide complet Windows + GPU
- ✅ Troubleshooting détaillé
- ✅ Checklist validation

---

## ❓ Questions fréquentes

### Q1 : Puis-je continuer depuis le checkpoint epoch=99 ?

**Non, pas recommandé**. Le modèle a déjà overfitté (`val_loss` augmente). Mieux vaut repartir du checkpoint français avec hyperparams corrigés.

### Q2 : Combien de temps va prendre le training ?

**Avec transfer learning** :
- GPU NVIDIA (RTX 3060+) : 6-12 heures
- Apple Silicon (M1/M2) : 12-24 heures
- CPU : 3-7 jours (pas recommandé)

**From scratch** : Multiplier par 4-5x

### Q3 : Puis-je utiliser mes fichiers macOS directement sur Windows ?

**Oui !** Le dataset et scripts sont 100% portables. Seules les dépendances système changent (CUDA vs MPS).

### Q4 : Comment savoir si le training se passe bien ?

**Regarder TensorBoard** :
- `loss_g` doit **descendre progressivement** (34 → 5 → 2)
- `val_loss` doit **descendre** aussi (pas augmenter)
- Si stagne après 50 epochs → Problème

### Q5 : Que faire si "CUDA out of memory" ?

**Réduire batch_size** :
```bash
python scripts/train_japanese_voice.py  # Éditer batch_size dans script
# Essayer : 32 → 16 → 8
```

---

## 🎯 Action immédiate recommandée

**1. Décider de la plateforme** :
- Vous avez accès à Windows + GPU NVIDIA ? → **Option A (recommandée)**
- Vous restez sur Mac M1/M2 ? → **Option B (plus lent mais fonctionne)**
- Ni l'un ni l'autre ? → **Option C (Google Colab gratuit)**

**2. Lancer le training** :
```bash
# Sur la plateforme choisie
python scripts/train_japanese_voice.py
```

**3. Monitorer avec TensorBoard** :
```bash
tensorboard --logdir ./lightning_logs --port 6006
```

**4. Attendre convergence** :
- Vérifier toutes les 2-3 heures
- Objectif : `loss_g < 5.0` et `val_loss < 10.0`

**5. Tester le modèle** :
```bash
# Export ONNX
python -m piper.train.export_onnx checkpoint.ckpt model.onnx

# Test
echo 'こんにちは' | piper -m model.onnx -f test.wav
```

---

**Bon courage pour le training ! 🚀**

Si questions ou problèmes, voir :
- `TRAINING_ON_WINDOWS_GPU.md` pour détails Windows
- `TRAINING_FAILURE_REPORT.md` pour analyse technique complète
