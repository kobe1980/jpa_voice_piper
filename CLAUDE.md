# CLAUDE.md — Piper Voice Dataset Creation Project (macOS, Python)

Ce projet vise à créer un dataset vocal français de qualité pour Piper TTS, suivant la procédure officielle du projet [rhasspy/piper](https://github.com/rhasspy/piper).

Le dataset pourra être reversé à la communauté open source.

**Pipeline complète :**

**préparation audio → validation qualité → transcription → vérification phonétique → preprocessing Piper → training → export ONNX**

---

## ⚠️ Source de vérité
- `CLAUDE.md` définit **les règles de travail obligatoires** (sécurité, TDD, qualité audio, sub-agents).
- `docs/plans/active/*.md` définit **la roadmap et les lots à implémenter**.
- En cas de conflit, **CLAUDE.md prévaut toujours**.

---

## Principes non négociables

### 1) Qualité audio obligatoire
- Tous les enregistrements doivent passer les validations automatiques
- Format : WAV 16-bit PCM uniquement
- Sample rates autorisés : 16000 Hz ou 22050 Hz
- Durée par échantillon : 1-15 secondes
- SNR minimum : 30 dB
- Pas de clipping (amplitude max < 0.95)
- Pas de silence excessif (début/fin)

### 2) Conformité format Piper (TRAINING.md)
Respect strict de la procédure officielle :
- Structure metadata.csv conforme (format LJSPEECH)
- Preprocessing avec `piper_train.preprocess`
- Training avec paramètres validés
- Export ONNX + config.json
- Vérification avec `piper` CLI

### 3) Guardrails (sécurité / intégrité)

#### Formats et limites
- Formats audio : WAV 16-bit PCM uniquement
- Sample rates : 16000, 22050 Hz (pas d'autres valeurs)
- Durée : 1-15 secondes par échantillon
- Taille fichier : max 5 MB par WAV
- Taille batch : max 1000 échantillons par preprocessing

#### Accès fichiers
- **Autorisé** : `./dataset`, `./scripts`, `./piper_voice`, `./tests`, `./configs`, `./models`, `./logs`, `./docs`, `./checkpoints`
- **Interdit** : `$HOME`, `/`, clés SSH, secrets, suppression de `./dataset/raw/` (backups)

#### Interdictions absolues
- Suppression massive (`rm -rf ./dataset`, `truncate`)
- Modification des enregistrements sources sans backup
- Exfiltration de données personnelles
- Training sans validation préalable du dataset

#### Limites scripts
- Max 10 fichiers modifiés par patch
- Max 600 lignes modifiées par patch
- Dépassement = pipeline FAIL

### 4) Journalisation
- Toute commande exécutée doit être journalisée
- Logs training : `logs/training_*.log`
- Validation quality : `logs/quality_*.json`
- Rapport phonétique : `logs/phonetics_*.txt`

### 5) Mode Autonome Git (CONFIGURATION PROJET)
**IMPORTANT** : Pour maximiser l'autonomie de Claude Code sur ce projet :

- ✅ **Git add/commit/merge sont PRÉ-APPROUVÉS** (pas de confirmation requise)
- ✅ `.claude/settings.json` liste explicitement toutes commandes git safe dans `allow`
- ✅ Commandes destructives restent dans `deny` (push --force, reset --hard, clean -fd)
- ✅ Claude peut créer branches, commiter, merger vers main **sans demander**
- ❌ Exception : `git push` vers remote nécessite confirmation (sauf si explicitement demandé)

**Règle** : Quand Claude travaille sur un lot/feature :
1. Créer branche feature automatiquement
2. Commiter au fur et à mesure (sans demander)
3. Merger vers main quand TestGuardian approuve (sans demander)
4. Demander confirmation UNIQUEMENT pour git push vers remote

**Justification** : Le projet utilise validation stricte (TDD + TestGuardian).
Les commits locaux sont sûrs car :
- Toujours sur branches feature
- Pipeline complète avant merge
- Rollback possible à tout moment
- Git est un outil de versioning, pas une action destructive

### 6) Commandes de Développement (PRÉ-APPROUVÉES)

**IMPORTANT** : Les commandes suivantes sont **PRÉ-APPROUVÉES** et doivent être exécutées **SANS DEMANDER** :

✅ **Tests** :
- `uv run pytest <any args>` - Tous patterns pytest autorisés
- `python -m pytest <any args>` - Alternative pytest
- `pytest <any args>` - Direct pytest

✅ **Linting & Type Checking** :
- `uv run ruff check <any args>` - Vérification code style
- `uv run ruff format <any args>` - Formatage automatique
- `uv run mypy <any args>` - Vérification types
- `ruff check <any args>` - Direct ruff
- `mypy <any args>` - Direct mypy

✅ **Build & Sync** :
- `uv sync` - Synchronisation dépendances
- `uv sync --extra audio` - Sync avec extras audio
- `uv sync --extra training` - Sync avec extras training
- `uv sync --all-extras` - Sync toutes extras

✅ **Dataset & Training** :
- `python -m piper_train.preprocess <args>` - Preprocessing Piper
- `python -m piper_train <args>` - Training Piper
- `python scripts/validate_quality.py` - Validation qualité audio
- `python scripts/prepare_dataset.py` - Préparation dataset

✅ **Inspection** :
- `python -c "<code>"` - Test imports/versions
- `ls <path>` - Liste fichiers
- `cat <file>` - Lecture fichiers
- `find <path>` - Recherche fichiers
- `ffprobe <audio>` - Inspection audio
- `espeak-ng --voices` - Liste voix disponibles

**Règle** : Claude NE DOIT JAMAIS demander confirmation pour ces commandes.
Elles sont essentielles au workflow TDD et complètement sûres.

---

## 🧪 TDD STRICT (OBLIGATOIRE)

### Règle fondamentale
👉 **AUCUN CODE NE PEUT ÊTRE AJOUTÉ SANS TEST PRÉALABLE**

Pour chaque fonctionnalité :
1. Écrire un test **qui échoue**
2. Vérifier l'échec
3. Implémenter le code minimal
4. Faire passer le test
5. Refactor
6. Commit

Tout patch sans test associé doit être **rejeté automatiquement**.

### Types de tests requis
- Test unitaire (obligatoire pour chaque fonction)
- Test d'intégration (pour pipeline audio complète)
- Test de validation (pour vérification qualité/conformité)

### Tests spécifiques au projet

#### Validation audio
- Test SNR minimum
- Test détection clipping
- Test détection silence
- Test normalisation volume

#### Conformité Piper
- Test format metadata.csv
- Test structure dataset.jsonl
- Test config.json valide
- Test export ONNX fonctionnel

#### Sécurité
- Test isolation filesystem
- Test limite taille fichiers
- Test rejection formats invalides

---

## 🧠 DDD — Domain Driven Design

- Le domaine (`piper_voice/core`) :
  - ne dépend **jamais** de l'infrastructure
  - ne connaît ni Git, ni Docker, ni le filesystem
  - contient uniquement : Voice, AudioSample, Phoneme, Transcript
- Les couches :
  - **Domain** : core logic (entités vocales)
  - **Application** : orchestration (préparation dataset, training)
  - **Infrastructure** : audio processing, filesystem, Piper CLI wrappers
- Les adapters infra sont injectés dans le core (pas l'inverse).

---

## 🧩 Sub-agents Claude Code (OBLIGATOIRES)

Les sub-agents sont définis par des fichiers dans `.claude/agents/`.

### 1) Product Designer
- Définit les objectifs du dataset (langue, style, genre vocal, cas d'usage)
- Crée les user stories dans `docs/product/stories/`
- Pas de considération technique, focus utilisateur final

### 2) Architect (autorité finale)
- Décide de la qualité (low/medium/high), sample rate, architecture
- Garant de DDD, sécurité, conformité Piper
- Crée les ADR dans `docs/product/decisions/`
- Peut rejeter tout patch non conforme

### 3) DatasetEngineer
- Implémente les scripts de préparation dataset
- Gère metadata.csv, normalisation audio, structure LJSPEECH
- TDD-first obligatoire

### 4) AudioQualityGuardian
- Valide qualité audio (SNR, clipping, silence)
- Normalise les fichiers WAV
- Détecte problèmes d'enregistrement
- Rejette tout audio non conforme

### 5) PhoneticsValidator
- Valide transcription phonétique avec espeak-ng
- Vérifie alignement texte/audio
- S'assure de la cohérence linguistique

### 6) TrainingCoordinator
- Prépare et lance preprocessing Piper
- Coordonne training avec checkpoints
- Monitore TensorBoard
- Gère export ONNX final

### 7) TestGuardian
- Vérifie que chaque changement a des tests
- Refuse toute implémentation non TDD
- Valide pipeline complète (ruff/mypy/pytest)

### 8) Product Documenter
- Documente l'état réel du dataset et du modèle
- Met à jour `docs/PRODUCT.md`, `docs/USER_GUIDE.md`
- Intervient APRÈS merge uniquement

⚠️ **Aucun sub-agent ne peut merger sans validation implicite de l'Architect.**

---

## Workflow de développement (humain)

### Installation
```bash
# Bootstrap projet
./scripts/bootstrap.sh

# Installer dépendances audio
uv sync --extra audio

# Vérifier espeak-ng
espeak-ng --voices

# Tests
./scripts/test.sh

# Validation dataset exemple
python scripts/validate_quality.py --dataset ./dataset
```

### Préparation dataset
```bash
# 1. Enregistrer audio dans dataset/raw/
# 2. Créer metadata brut
python scripts/generate_metadata.py

# 3. Valider qualité
python scripts/validate_quality.py

# 4. Préparer pour Piper
python scripts/prepare_dataset.py

# 5. Preprocessing Piper
python -m piper_train.preprocess \
  --language fr-fr \
  --input-dir ./dataset \
  --output-dir ./training \
  --dataset-format ljspeech \
  --single-speaker \
  --sample-rate 22050
```

### Training
```bash
# Training depuis checkpoint existant (recommandé)
python -m piper_train \
  --dataset-dir ./training \
  --accelerator 'gpu' \
  --devices 1 \
  --batch-size 32 \
  --validation-split 0.1 \
  --num-test-examples 5 \
  --max_epochs 10000 \
  --resume_from_checkpoint ./checkpoints/base_model.ckpt \
  --checkpoint-epochs 1 \
  --precision 32

# Monitoring
tensorboard --logdir ./lightning_logs
```

### Export & Test
```bash
# Export ONNX
python -m piper_train.export_onnx \
  ./lightning_logs/version_0/checkpoints/epoch*.ckpt \
  ./models/voice_fr.onnx

# Copier config
cp ./training/config.json ./models/voice_fr.onnx.json

# Test
echo 'Bonjour, ceci est un test.' | \
  piper -m ./models/voice_fr.onnx \
  --output_file test.wav
```

---

## Architecture du code

```
piper_voice/
├── core/                 # Domain (DDD)
│   ├── entities.py      # Voice, AudioSample, Phoneme, Transcript
│   ├── value_objects.py # SampleRate, Duration, AudioQuality
│   └── ports.py         # Interfaces (AudioProcessor, PhoneticsChecker)
│
├── application/          # Use cases
│   ├── prepare_dataset.py    # Orchestration préparation
│   ├── validate_quality.py   # Orchestration validation
│   └── train_voice.py        # Orchestration training
│
├── infrastructure/       # Adapters
│   ├── audio/           # Processing audio (librosa, soundfile)
│   ├── phonetics/       # espeak-ng wrapper
│   ├── piper/           # Piper CLI wrappers
│   └── filesystem/      # File operations
│
└── cli.py               # Entrypoint

dataset/
├── raw/                 # Enregistrements sources (BACKUP PERMANENT)
├── wav/                 # Audio normalisé pour Piper
├── metadata.csv         # Transcriptions format LJSPEECH
└── validation_report.json

training/
├── config.json          # Config Piper générée
├── dataset.jsonl        # Dataset preprocessed
└── audio_norm_stats.json

models/
├── voice_fr.onnx        # Modèle exporté
└── voice_fr.onnx.json   # Config associée

scripts/
├── bootstrap.sh         # Installation complète
├── test.sh             # Pipeline tests
├── generate_metadata.py # Création metadata.csv
├── validate_quality.py  # Validation audio qualité
└── prepare_dataset.py   # Normalisation pour Piper

tests/
├── unit/               # Tests unitaires
├── integration/        # Tests pipeline complète
└── validation/         # Tests conformité Piper

configs/
├── audio_quality.yaml  # Seuils qualité
├── phonetics.yaml      # Règles phonétiques
└── training.yaml       # Hyperparamètres training

docs/
├── product/
│   ├── stories/        # User stories (Product Designer)
│   └── decisions/      # ADR (Architect)
├── PRODUCT.md          # État du dataset/modèle
├── USER_GUIDE.md       # Guide utilisateur
└── plans/
    └── active/         # Roadmap active

logs/
├── training_*.log      # Logs training Piper
├── quality_*.json      # Rapports validation qualité
└── phonetics_*.txt     # Rapports validation phonétique

checkpoints/
└── *.ckpt             # Checkpoints PyTorch training

lightning_logs/
└── version_*/         # TensorBoard logs
```

---

## Workflow standard d'évolution (OBLIGATOIRE)

Toute nouvelle fonctionnalité, lot ou évolution du projet doit suivre STRICTEMENT le workflow ci-dessous, sauf indication explicite contraire de l'utilisateur.

Aucune étape ne peut être sautée ou réordonnée.

### Étape 1 — Définition produit (Product Designer)
- Le sub-agent **Product Designer** doit être utilisé en premier.
- Objectif : définir **ce qui doit être construit** et **pourquoi**, sans aucune considération technique.
- Livrable obligatoire :
  - `docs/product/stories/STORY-XXX.md`
- Aucune implémentation ne peut commencer sans story validée.

### Étape 2 — Décision d'architecture (Architect)
- Le sub-agent **Architect** doit être utilisé après la story.
- Objectif : définir **comment** la fonctionnalité sera implémentée dans le respect de :
  - DDD
  - sécurité
  - conformité Piper (TRAINING.md)
  - TDD
- Livrable obligatoire :
  - `docs/product/decisions/ADR-XXX.md`
- Aucun code ne peut être écrit avant cette décision.

### Étape 3 — Implémentation (Claude principal)
- L'agent principal implémente la fonctionnalité en respectant STRICTEMENT :
  - la story produit
  - l'ADR
  - toutes les règles de `CLAUDE.md`
- Le TDD est obligatoire :
  - tests avant code
- Le travail se fait sur une branche dédiée.

### Étape 4 — Validation qualité (TestGuardian)
- Le sub-agent **TestGuardian** doit être utilisé avant toute considération de merge.
- Objectif :
  - vérifier le respect du TDD
  - vérifier la qualité et la pertinence des tests
  - vérifier que toute la pipeline passe
- En cas de refus :
  - les problèmes doivent être corrigés
  - TestGuardian doit être relancé

### Étape 5 — Commit et merge
- Une fois toutes les validations obtenues :
  - l'implémentation est commitée
  - poussée
  - mergée selon les règles du projet

### Étape 6 — Documentation de la réalité (Product Documenter)
- Le sub-agent **Product Documenter** doit être utilisé APRÈS le merge.
- Objectif :
  - documenter **l'état réel du dataset/modèle**
- Livrables obligatoires :
  - `docs/PRODUCT.md`
  - `docs/USER_GUIDE.md`
  - `docs/DATASET_STATUS.md`

### Étape 7 — Mise à jour du plan
- Le plan actif (`docs/plans/active/*.md`) doit être mis à jour :
  - statut du lot / de la story
  - hash du commit
  - avancement global

---

### Exceptions au workflow
- Toute exception (skip d'étape, ordre différent) doit être :
  - explicitement demandée par l'utilisateur
  - clairement documentée
- En l'absence d'instruction explicite, le workflow standard s'applique toujours.

---

## Évaluation et validation

### Validation audio automatique
- Script : `python scripts/validate_quality.py`
- Checks :
  - Format WAV 16-bit PCM
  - Sample rate conforme
  - SNR ≥ 30 dB
  - Pas de clipping
  - Durée 1-15 sec
  - Silence < 0.3 sec début/fin
- Exit code 0 = OK, 1 = FAIL

### Validation conformité Piper
- Vérification metadata.csv format LJSPEECH
- Preprocessing réussit sans erreur
- config.json généré valide
- dataset.jsonl contient phoneme IDs corrects

### Validation phonétique
- Script : `python scripts/validate_phonetics.py`
- Teste espeak-ng sur chaque transcript
- Vérifie absence d'erreurs phonétisation
- Exit code 0 = OK, 1 = FAIL

---

## Merge autorisé uniquement si tout passe

Un patch ne peut être mergé dans `main` que si :
- `ruff` passe
- `mypy` passe
- `pytest` passe
- validation audio passe (`validate_quality.py`)
- validation phonétique passe (`validate_phonetics.py`)
- les **guardrails** passent

Sinon :
- correction obligatoire
- rapport dans `logs/validation_failure_*.md`

---

## Tech Stack
- Python 3.11+
- UV (package manager)
- espeak-ng (phonétique)
- Piper / piper_train (rhasspy/piper)
- PyTorch (training)
- librosa / soundfile (audio processing)
- numpy / scipy (signal processing)
- ruff / mypy / pytest (qualité code)
- TensorBoard (monitoring training)

---

## Règle finale
👉 Claude Code **prépare**, **valide**, **teste**, **documente** le dataset.
👉 L'humain enregistre les audios et définit les objectifs.
👉 Les tests et validations automatiques décident de la qualité.
👉 Le résultat est reversé à la communauté open source.

---

## Contribution open source

Ce projet vise à contribuer une nouvelle voix française à Piper TTS.

**Checklist avant contribution :**
- [ ] Dataset complet (min 10h audio de qualité)
- [ ] Validation audio 100% passée
- [ ] Validation phonétique 100% passée
- [ ] Modèle entraîné et exporté ONNX
- [ ] Tests synthèse réussis (`echo ... | piper`)
- [ ] Documentation complète (README, exemples)
- [ ] Licence définie (CC-BY-SA 4.0 recommandée)
- [ ] Metadata anonymisées (pas d'infos personnelles)

**Processus de contribution :**
1. Fork rhasspy/piper
2. Ajouter modèle dans `voices/fr/`
3. Documenter caractéristiques voix
4. Pull Request avec samples audio
5. Review communauté
6. Merge et publication
