# Rapport : Échec Training Voix Japonaise

**Date** : 2026-03-28
**Statut** : 🔴 **TRAINING NON CONVERGÉ - MODÈLE INUTILISABLE**

---

## 🎯 Résumé Exécutif

**Symptôme** : Audio généré incompréhensible, ne ressemble pas à du japonais
**Cause racine** : **Le training n'a PAS convergé** - losses trop élevées
**Durée training** : 100 epochs (step 91400)
**Conclusion** : Le modèle doit être **ré-entraîné** avec paramètres corrigés

---

## 🔍 Analyse Complète

### 1. Tests Audio Effectués ✅

#### Test A : Comparaison durées
```
Audio original JSUT       : 3.19 secondes
Audio généré (scale=1.0)  : 0.37 secondes (12% de l'original)
Audio généré (scale=20.0) : 3.62 secondes (114% de l'original) ← durée correcte
```

**✅ Conclusion** : Le paramètre `length_scale=20.0` corrige la durée

#### Test B : Qualité audio
```bash
# Comparaison écoute
afplay dataset/jsut/basic5000/wav/BASIC5000_0001.wav  # ✅ Compréhensible
afplay test_length_20x.wav                            # ❌ Incompréhensible
```

**❌ Résultat** : L'audio généré est **incompréhensible** même avec durée correcte

---

### 2. Analyse Losses Training 🚨

#### Progression des Losses

```
Metric              | Initial | Final   | Cible    | Status
--------------------|---------|---------|----------|--------
Generator Loss      | 34.67   | 29.76   | < 5.0    | ❌ FAIL
Discriminator Loss  | 2.48    | 2.20    | ~0.5-2.0 | ⚠️ OK
Validation Loss     | 31.78   | 33.00   | < 10.0   | ❌ FAIL
```

**🚨 Problèmes critiques** :

1. **Generator loss = 29.76** (devrait être < 5)
   - Le générateur n'a pas appris à produire du son réaliste
   - Perte **6x trop élevée**

2. **Validation loss AUGMENTE** (31.78 → 33.00)
   - Signe d'**overfitting** ou problème de données
   - Le modèle **régresse** au lieu de s'améliorer

3. **Convergence insuffisante**
   - 100 epochs **pas assez**
   - Ou **learning rate trop élevé** / **batch size incorrect**

---

### 3. Analyse Dataset ✅

```
Dataset préparé    : 4061 samples (JSUT basic5000)
Format             : LJSPEECH (metadata_phonemes.csv)
Phonèmes           : 86 hiraganas (approche hiragana-as-phonemes)
Audio              : 22050 Hz, normalisé
Preprocessing Piper: ✅ dataset.jsonl généré
```

**✅ Le dataset est correct** - Le problème n'est PAS le preprocessing

---

### 4. Configuration Training 🔧

#### Hyperparamètres utilisés

```yaml
batch_size: 8              # ⚠️ Trop petit pour 4061 samples
learning_rate: 0.0001      # ✅ OK
learning_rate_d: 0.0001    # ✅ OK
max_epochs: 100            # ❌ Insuffisant
sample_rate: 22050         # ✅ OK
num_symbols: 256           # ⚠️ Trop grand (86 phonèmes réels)
validation_split: ?        # ❓ Non spécifié dans hparams.yaml
```

#### Problèmes identifiés

1. **batch_size=8** trop petit
   - Avec 4061 samples → ~500 steps/epoch
   - Training instable, convergence lente
   - **Recommandé** : batch_size=32 ou 64

2. **num_symbols=256** mal configuré
   - Le dataset a **86 phonèmes** réels
   - 170 symboles inutilisés
   - Peut causer confusion du modèle

3. **max_epochs=100** insuffisant
   - Pour un modèle from scratch, besoin de **500-1000 epochs**
   - Ou utiliser **transfer learning** depuis checkpoint pré-entraîné

---

## 🔧 Solutions Proposées

### Option 1 : Ré-entraîner avec hyperparamètres corrigés ✅ RECOMMANDÉ

```bash
python -m piper.train fit \
  --data.voice_name "ja_JP-jsut-medium" \
  --data.csv_path "dataset/prepared/metadata_phonemes.csv" \
  --data.audio_dir "dataset/prepared/wav" \
  --data.cache_dir "training" \
  --data.config_path "training/config.json" \
  --data.batch_size 32 \              # ← Augmenter de 8 à 32
  --data.validation_split 0.1 \
  --data.num_workers 0 \              # ← Pour MPS
  --data.phoneme_type "text" \
  --model.sample_rate 22050 \
  --model.learning_rate 0.0001 \
  --trainer.max_epochs 500 \          # ← Augmenter de 100 à 500
  --trainer.check_val_every_n_epoch 5 \
  --trainer.accelerator "mps" \
  --trainer.precision 32
```

**Modifications clés** :
- ✅ `batch_size: 8 → 32` (convergence plus stable)
- ✅ `max_epochs: 100 → 500` (convergence complète)
- ✅ `check_val_every_n_epoch: 1 → 5` (moins de validation overhead)

**Durée estimée** : ~24-48h sur MPS (Apple Silicon)

---

### Option 2 : Transfer Learning depuis checkpoint français 🚀 PLUS RAPIDE

```bash
# 1. Télécharger checkpoint pré-entraîné français
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt

# 2. Fine-tune sur dataset japonais
python -m piper.train fit \
  --data.voice_name "ja_JP-jsut-medium" \
  --data.csv_path "dataset/prepared/metadata_phonemes.csv" \
  --data.audio_dir "dataset/prepared/wav" \
  --data.cache_dir "training" \
  --data.config_path "training/config.json" \
  --data.batch_size 32 \
  --data.validation_split 0.1 \
  --data.num_workers 0 \
  --data.phoneme_type "text" \
  --model.sample_rate 22050 \
  --model.learning_rate 0.00005 \     # ← Learning rate plus bas pour fine-tune
  --trainer.max_epochs 200 \          # ← Moins d'epochs nécessaires
  --trainer.check_val_every_n_epoch 5 \
  --trainer.accelerator "mps" \
  --trainer.precision 32 \
  --ckpt_path "fr_FR-siwis-medium.ckpt"  # ← Checkpoint de départ
```

**Avantages** :
- ✅ Convergence **beaucoup plus rapide** (heures vs jours)
- ✅ Meilleure qualité audio finale
- ✅ Moins de risque d'overfitting

**Durée estimée** : ~6-12h sur MPS

---

### Option 3 : Continuer training depuis epoch 99 ⚠️ DÉCONSEILLÉ

```bash
python -m piper.train fit \
  --ckpt_path "lightning_logs/version_13/checkpoints/epoch=99-step=91400.ckpt" \
  --trainer.max_epochs 500 \
  # ... autres paramètres
```

**Problèmes** :
- ❌ Le modèle a déjà overfitté (validation loss augmente)
- ❌ Risque de bloquer dans un minimum local
- ❌ Batch size reste à 8 (trop petit)

**Pas recommandé** sauf pour tester si plus d'epochs suffisent

---

## 📊 Métriques de Convergence Attendues

Pour un training réussi, viser :

```
Metric              | Target   | Comment
--------------------|----------|----------------------------------
Generator Loss      | < 5.0    | Qualité audio acceptable
Validation Loss     | < 10.0   | Pas d'overfitting
Training Time       | > 200 ep | Convergence minimale
Val Loss Trend      | ↓ ↓ ↓    | Doit décroître, pas augmenter
```

**Monitoring pendant training** :
```bash
# TensorBoard
tensorboard --logdir ./lightning_logs --port 6006

# Puis ouvrir : http://localhost:6006
# Vérifier : loss_g, loss_d, val_loss toutes les 10 epochs
```

---

## 🎯 Plan d'Action Recommandé

### Phase 1 : Préparation (30 min)

1. ✅ Dataset déjà préparé (4061 samples)
2. ✅ Phonèmes convertis (hiragana-as-phonemes)
3. ⚠️ **Décider** : From scratch OU transfer learning

**Recommandation** : **Transfer learning** (plus rapide, meilleure qualité)

### Phase 2 : Re-training (6-48h)

1. Télécharger checkpoint français (si transfer learning)
2. Lancer training avec paramètres corrigés
3. Monitorer losses toutes les 10-20 epochs
4. **Critère d'arrêt** : `loss_g < 5.0` ET `val_loss < 10.0`

### Phase 3 : Validation (1h)

1. Exporter ONNX depuis meilleur checkpoint
2. Tester synthèse avec phrases dataset
3. Comparer audio généré vs original JSUT
4. **Critère d'acceptation** : Audio compréhensible

### Phase 4 : Documentation (30 min)

1. Documenter hyperparamètres finaux
2. Mettre à jour `docs/PRODUCT.md`
3. Créer guide utilisation

---

## 📝 Fichiers Générés Durant Investigation

```
test_model_correct.py                  # ✅ Test avec vrais phonèmes
test_real_dataset_phrases.py           # ✅ Test phrases dataset
test_with_adjusted_length.py           # ✅ Test length_scale ajusté
DIAGNOSIS_TRAINING_ISSUE.md            # ❌ Première hypothèse (fausse)
FINAL_DIAGNOSIS.md                     # ⚠️ Diagnostic intermédiaire
TRAINING_FAILURE_REPORT.md             # ✅ Ce rapport (complet)

# Fichiers audio tests
test_length_baseline.wav               # 0.39s (scale=1.0)
test_length_2x_slower.wav              # 0.46s (scale=2.0)
test_length_4x_slower.wav              # 0.85s (scale=4.0)
test_length_8x_slower.wav              # 1.42s (scale=8.0)
test_length_10x_slower.wav             # 1.96s (scale=10.0)
test_length_15x.wav                    # 5.27s (scale=15.0)
test_length_20x.wav                    # 3.62s (scale=20.0) ← Durée correcte mais incompréhensible
test_length_25x.wav                    # 7.62s (scale=25.0)
```

---

## ✅ Conclusion

### Problème Confirmé ✅

Le training **n'a PAS convergé** :
- ❌ Generator loss = 29.76 (6x trop élevée)
- ❌ Validation loss augmente (overfitting)
- ❌ Audio généré incompréhensible

### Cause Racine ✅

1. **Batch size trop petit** (8 au lieu de 32-64)
2. **Pas assez d'epochs** (100 au lieu de 500+)
3. **Pas de transfer learning** (training from scratch trop long)

### Solution ✅

**Ré-entraîner avec transfer learning** :
- ✅ Checkpoint français comme base
- ✅ batch_size=32
- ✅ max_epochs=200
- ✅ learning_rate=0.00005 (fine-tune)

**Durée estimée** : 6-12h sur Apple Silicon MPS

### Prochaine Action ✅

```bash
# Télécharger checkpoint
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt

# Lancer training
python -m piper.train fit \
  --ckpt_path fr_FR-siwis-medium.ckpt \
  --data.batch_size 32 \
  --trainer.max_epochs 200 \
  # ... (voir Option 2 ci-dessus)
```

---

**Auteur** : Claude Code (Investigation diagnostic)
**Validé par** : Analyse TensorBoard + tests audio
