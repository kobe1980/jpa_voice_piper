# PLAN-001: French Voice Dataset Creation

**STATUS**: 🟢 ACTIVE
**Date**: 2026-03-08
**Last Updated**: 2026-03-08
**Completion**: 15% (Phase 1 complete)

---

## Objectif Global

Créer un dataset vocal français de haute qualité pour Piper TTS, suivant la procédure officielle du projet rhasspy/piper, qui pourra être reversé à la communauté open source.

**Pipeline complète** :
audio preparation → quality validation → transcription → phonetic verification → Piper preprocessing → training → ONNX export

---

## Phase 1: Foundation (Domain Layer) ✅ COMPLETE

**Commit**: 76ff7eb
**Branch**: main
**Status**: ✅ MERGED
**Date**: 2026-03-08

### Ce qui a été implémenté

#### Domain Layer (100% complet)
- ✅ Value Objects (SampleRate, Duration, AudioFormat, AudioQuality)
- ✅ Entities (Phoneme, Transcript, AudioSample, Voice)
- ✅ Ports (5 interfaces: AudioProcessor, PhoneticsChecker, FileSystem, MetadataRepository, PiperTraining)
- ✅ Tests complets (36 tests unitaires, 100% couverture domaine)

#### Infrastructure de développement
- ✅ Structure projet (pyproject.toml, répertoires)
- ✅ Scripts bootstrap et test
- ✅ Quality gates (ruff, mypy, pytest)

### Validation
- ✅ TestGuardian: Approuvé
- ✅ Product Documenter: Documentation créée
- ✅ ADR-001: Respecté
- ✅ STORY-001: Phase 1 complète

---

## Phase 2: Infrastructure Layer (Audio & FileSystem) 🔴 NOT STARTED

**Objectif** : Implémenter les adapters d'infrastructure pour le traitement audio et le filesystem sécurisé.

### Stories à créer
1. **STORY-002**: Audio Processing Infrastructure
   - Adapter librosa/soundfile pour AudioProcessorPort
   - Chargement, analyse qualité, normalisation audio
   - Tests d'intégration avec fichiers audio réels

2. **STORY-003**: Safe Filesystem Infrastructure
   - Adapter filesystem avec guardrails de sécurité
   - Restrictions chemins (dataset/, scripts/, etc.)
   - Tests de validation sécurité

### Livrables attendus
- `/piper_voice/infrastructure/audio/processor.py` (implémente AudioProcessorPort)
- `/piper_voice/infrastructure/filesystem/safe_fs.py` (implémente FileSystemPort)
- Tests d'intégration audio (analyse SNR, clipping, normalisation)
- Tests de sécurité filesystem (rejets chemins interdits)

### Dépendances techniques
- librosa >= 0.10.0 (déjà dans pyproject.toml)
- soundfile >= 0.12.0 (déjà dans pyproject.toml)

### Critères de validation
- ✅ Peut charger fichiers WAV et extraire sample rate, durée
- ✅ Peut analyser qualité (SNR, clipping, silence)
- ✅ Peut normaliser audio vers 22050 Hz mono
- ✅ Rejette accès fichiers hors zones autorisées
- ✅ Tests d'intégration passent avec fixtures audio réelles
- ✅ TestGuardian approuve

**Estimation** : 1 semaine
**Assigné** : À définir
**Priorité** : HIGH (bloquant pour Phase 3)

---

## Phase 3: Infrastructure Layer (Phonetics & Metadata) 🔴 NOT STARTED

**Objectif** : Implémenter validation phonétique et gestion metadata LJSPEECH.

### Stories à créer
1. **STORY-004**: Phonetics Validation Infrastructure
   - Wrapper espeak-ng pour PhoneticsCheckerPort
   - Validation transcriptions françaises
   - Conversion texte → phoneme IDs

2. **STORY-005**: Metadata Management Infrastructure
   - Adapter LJSPEECH format pour MetadataRepositoryPort
   - Lecture/écriture metadata.csv
   - Validation format conformité Piper

### Livrables attendus
- `/piper_voice/infrastructure/phonetics/espeak_adapter.py`
- `/piper_voice/infrastructure/filesystem/metadata.py`
- Tests validation phonétique avec espeak-ng
- Tests format LJSPEECH

### Dépendances techniques
- espeak-ng (installation système requise)
- Validation format Piper (TRAINING.md)

### Critères de validation
- ✅ Peut valider texte français avec espeak-ng
- ✅ Peut générer phoneme IDs corrects
- ✅ Peut lire/écrire metadata.csv format LJSPEECH
- ✅ Rejette metadata non conforme
- ✅ Tests intégration espeak-ng passent
- ✅ TestGuardian approuve

**Estimation** : 1 semaine
**Dépend de** : Phase 2 (FileSystem)
**Priorité** : HIGH (bloquant pour Phase 4)

---

## Phase 4: Application Layer (Use Cases) 🔴 NOT STARTED

**Objectif** : Implémenter les cas d'usage métier orchestrant l'infrastructure.

### Stories à créer
1. **STORY-006**: Quality Validation Use Case
   - Orchestration validation qualité complète
   - Génération rapports validation
   - Rejection automatique audio non conforme

2. **STORY-007**: Dataset Preparation Use Case
   - Orchestration préparation complète dataset
   - Normalisation batch audio
   - Génération metadata.csv

3. **STORY-008**: Phonetics Validation Use Case
   - Validation batch transcriptions
   - Détection erreurs phonétisation
   - Génération rapports phonétiques

### Livrables attendus
- `/piper_voice/application/validate_quality.py`
- `/piper_voice/application/prepare_dataset.py`
- `/piper_voice/application/validate_phonetics.py`
- Tests use cases avec mocks infrastructure
- Tests intégration end-to-end

### Critères de validation
- ✅ Peut valider qualité répertoire complet audio
- ✅ Peut préparer dataset complet pour Piper
- ✅ Peut valider phonétisation batch transcriptions
- ✅ Génère rapports utilisables (JSON, logs)
- ✅ Tests intégration pipeline complète passent
- ✅ TestGuardian approuve

**Estimation** : 1-2 semaines
**Dépend de** : Phase 2 + Phase 3
**Priorité** : HIGH (bloquant pour Phase 5)

---

## Phase 5: CLI & User Scripts 🔴 NOT STARTED

**Objectif** : Créer interface utilisateur (CLI + scripts) pour interaction humaine.

### Stories à créer
1. **STORY-009**: CLI Interface
   - Implémentation `piper-voice` CLI
   - Commandes: validate, prepare, train, export
   - Help et documentation inline

2. **STORY-010**: User Utility Scripts
   - `scripts/generate_metadata.py`
   - `scripts/validate_quality.py`
   - `scripts/validate_phonetics.py`
   - `scripts/prepare_dataset.py`

### Livrables attendus
- `/piper_voice/cli.py` (implémentation complète)
- 4 scripts utilitaires fonctionnels
- Documentation USER_GUIDE.md mise à jour
- Exemples d'utilisation complets

### Critères de validation
- ✅ `piper-voice --help` fonctionne
- ✅ `piper-voice validate dataset/raw/` valide qualité
- ✅ `piper-voice prepare dataset/raw/ dataset/` prépare dataset
- ✅ Tous scripts fonctionnent standalone
- ✅ Documentation USER_GUIDE complète et testée
- ✅ TestGuardian approuve

**Estimation** : 1 semaine
**Dépend de** : Phase 4
**Priorité** : MEDIUM (permet utilisation par humains)

---

## Phase 6: Training Infrastructure 🔴 NOT STARTED

**Objectif** : Intégration complète Piper training (preprocessing, training, export).

### Stories à créer
1. **STORY-011**: Piper Training Infrastructure
   - Wrapper piper_train pour PiperTrainingPort
   - Preprocessing orchestration
   - Training coordination avec checkpoints
   - Export ONNX

2. **STORY-012**: Training Monitoring
   - TensorBoard integration
   - Progress tracking
   - Checkpoint management

### Livrables attendus
- `/piper_voice/infrastructure/piper/training_adapter.py`
- `/piper_voice/application/train_voice.py`
- Configuration templates (configs/*.yaml)
- Documentation TRAINING.md

### Critères de validation
- ✅ Peut lancer preprocessing Piper
- ✅ Peut entraîner modèle avec checkpoints
- ✅ Peut exporter ONNX fonctionnel
- ✅ Monitoring TensorBoard opérationnel
- ✅ Tests intégration Piper complets
- ✅ TestGuardian approuve

**Estimation** : 2-3 semaines
**Dépend de** : Phase 4 + Phase 5
**Priorité** : MEDIUM (permet training voix)

---

## Métriques de Succès Globales

### Technique
- [ ] 100% tests passent (toutes phases)
- [ ] Coverage ≥ 90% (domain: 100%, infra: 80%, app: 90%)
- [ ] Tous quality gates passent (ruff, mypy, pytest)
- [ ] Documentation à jour (PRODUCT.md, USER_GUIDE.md, DATASET_STATUS.md)

### Fonctionnel
- [ ] Peut valider 100+ échantillons audio
- [ ] Peut préparer dataset complet format Piper
- [ ] Peut entraîner modèle ONNX fonctionnel
- [ ] Voix synthétisée intelligible français

### Qualité Dataset
- [ ] Minimum 10 heures audio de qualité
- [ ] 100% échantillons SNR ≥ 30 dB
- [ ] 100% validation phonétique pass
- [ ] Format LJSPEECH conforme

### Open Source
- [ ] Dataset reversé communauté
- [ ] Documentation complète utilisateurs
- [ ] Licence définie (CC-BY-SA 4.0 recommandée)
- [ ] README clair et exemples fonctionnels

---

## Roadmap Timeline

| Phase | Durée Estimée | Status | Completion |
|-------|---------------|--------|------------|
| Phase 1: Foundation | 1 semaine | ✅ COMPLETE | 100% |
| Phase 2: Infra Audio/FS | 1 semaine | 🔴 NOT STARTED | 0% |
| Phase 3: Infra Phonetics/Metadata | 1 semaine | 🔴 NOT STARTED | 0% |
| Phase 4: Application Use Cases | 1-2 semaines | 🔴 NOT STARTED | 0% |
| Phase 5: CLI & Scripts | 1 semaine | 🔴 NOT STARTED | 0% |
| Phase 6: Training | 2-3 semaines | 🔴 NOT STARTED | 0% |
| **TOTAL** | **7-10 semaines** | **IN PROGRESS** | **15%** |

---

## Risques Identifiés

### Technique
1. **Dépendance espeak-ng** : Peut nécessiter compilation personnalisée voix française
2. **Performance librosa** : Traitement batch peut être lent (>1000 fichiers)
3. **Piper training** : Nécessite GPU/ressources importantes

### Process
1. **Scope creep** : Phases 2-6 peuvent révéler complexités additionnelles
2. **TDD discipline** : Maintenir tests-first strict sur 10 semaines difficile
3. **Documentation drift** : Risque docs deviennent obsolètes sans mises à jour continues

### Qualité
1. **Coverage maintien** : Risque couverture baisse avec croissance codebase
2. **Integration tests** : Peuvent devenir lents (>1 min) avec vrais fichiers audio
3. **Test data** : Nécessite fixtures audio réalistes mais licence compatible

---

## Prochaines Actions Immédiates

1. **Créer STORY-002** (Audio Processing Infrastructure)
   - Définir acceptance criteria détaillés
   - Créer ADR si décisions architecture nécessaires
   - Lancer workflow standard (Product Designer → Architect → Implémentation)

2. **Installer espeak-ng**
   - Vérifier disponibilité voix française
   - Tester phonétisation exemples français
   - Documenter installation macOS/Linux

3. **Créer fixtures audio test**
   - Enregistrer 10-20 échantillons test (libres droits)
   - Varier qualité (bon SNR, clipping, silence excessif)
   - Stocker dans tests/fixtures/audio/

4. **Mettre à jour README.md**
   - Clarifier statut "Foundation Only"
   - Ajouter badge "Phase 1 Complete"
   - Documenter roadmap phases suivantes

---

## Workflow Standard (Rappel)

Pour chaque nouvelle story :

1. **Product Designer** → créer story `docs/product/stories/STORY-XXX.md`
2. **Architect** → créer ADR `docs/product/decisions/ADR-XXX.md` (si nécessaire)
3. **Implémentation** → TDD strict (tests avant code)
4. **TestGuardian** → validation avant merge
5. **Commit + Merge** → feature branch → main
6. **Product Documenter** → mise à jour documentation réalité
7. **Update Plan** → mise à jour ce fichier avec progression

---

## Notes

- Ce plan est un document vivant, mis à jour après chaque story complétée
- Chaque phase peut révéler stories additionnelles non anticipées
- Les estimations sont indicatives, à ajuster selon réalité terrain
- Priorité : maintenir qualité et tests plutôt que vitesse implémentation
