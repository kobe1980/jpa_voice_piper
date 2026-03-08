# STORY-005: Piper Training Integration

## Title
Train Japanese Voice Model from Preprocessed Dataset

## Context / Problem

A voice dataset creator has completed dataset preparation: Japanese audio is recorded, transcripts are phonemized, and preprocessing has generated the training-ready files (dataset.jsonl, config.json, audio_norm_stats.json). However, these files alone do not produce a working voice model. The actual neural network training must now occur.

Piper uses a sophisticated VITS (Variational Inference with adversarial learning for end-to-end Text-to-Speech) architecture that requires careful training management:

- Training can take hours to days depending on dataset size and hardware
- The process must be interruptible and resumable (users cannot predict when interruptions occur)
- Training progress must be observable (users need to know if training is working)
- Starting from a base model dramatically reduces training time (transfer learning)
- Multiple checkpoints must be preserved to recover from failures or compare quality
- Training parameters significantly impact final voice quality and convergence speed

Without proper training integration, users face:
- No visibility into training progress (is it working or stuck?)
- Lost progress when interruptions occur (power failure, system crash, user stop)
- Uncertainty about when to stop training (has the model converged?)
- Difficulty reproducing results (what parameters were used?)
- No way to leverage existing models for faster training (must train from scratch)

## User Goal

As a voice dataset creator, I want to train a Japanese TTS voice model using my preprocessed data so that I can generate natural-sounding Japanese speech from text input.

## Functional Behavior

### Training Initialization

1. The user initiates training by providing:
   - Path to the preprocessed dataset directory (containing dataset.jsonl, config.json, audio_norm_stats.json)
   - Training configuration parameters (batch size, learning rate, epochs, etc.)
   - Optional: Path to a base checkpoint for transfer learning (recommended for faster convergence)
   - Optional: Path to resume from a previous training checkpoint (for interrupted training)

2. The system validates prerequisites before starting:
   - Verifies all required preprocessed files exist and are correctly formatted
   - Checks that dataset.jsonl is not empty and contains valid phoneme sequences
   - Confirms config.json has all required training parameters
   - Validates that the base checkpoint (if provided) is compatible with the dataset
   - Confirms sufficient disk space for checkpoints and logs
   - Detects available hardware (GPU, MPS, or CPU) and configures accordingly

3. The system initializes the training environment:
   - Loads the preprocessed dataset into memory-efficient data loaders
   - Initializes the VITS neural network architecture
   - If a base checkpoint is provided, loads the pre-trained weights (transfer learning)
   - If resuming from checkpoint, loads the exact training state (optimizer, epoch count, etc.)
   - Configures the optimizer with the specified learning rate
   - Sets up validation split (typically 10% of data) for quality monitoring

### Training Execution

4. Training begins and proceeds in epochs (complete passes through the dataset):
   - Each epoch processes all audio samples in batches
   - For each batch, the system computes training loss and updates model weights
   - Loss decreases over time as the model learns Japanese pronunciation patterns
   - The system automatically tracks multiple loss components (reconstruction, adversarial, duration, etc.)

5. Progress monitoring displays real-time information:
   - Current epoch number and total epochs
   - Training loss (should decrease consistently)
   - Validation loss (indicates generalization quality)
   - Estimated time remaining
   - Checkpoint save events

6. Automatic checkpointing occurs at regular intervals (e.g., every 5-10 epochs):
   - Saves the complete training state (model weights, optimizer state, epoch number)
   - Preserves multiple checkpoints to allow recovery from corrupted saves
   - Checkpoint filenames include epoch number for easy identification
   - User can resume training from any saved checkpoint

### Validation and Quality Monitoring

7. Periodic validation runs on the validation split:
   - Tests the model on audio samples not used for training
   - Computes validation loss to detect overfitting (training loss decreases but validation loss increases)
   - Generates sample audio outputs at key milestones (every 50 epochs) for human quality assessment
   - User can listen to samples to judge voice naturalness and pronunciation accuracy

8. TensorBoard integration provides visual monitoring:
   - Real-time loss curves (training and validation)
   - Learning rate schedule visualization
   - Audio spectrograms showing pronunciation quality improvements
   - User can open TensorBoard in browser to inspect training progress

### Training Completion and Interruption Handling

9. Training continues until one of these conditions:
   - Maximum epoch count reached (user-specified limit)
   - Early stopping triggered (validation loss stops improving for N epochs)
   - User manually stops training (Ctrl+C or system signal)
   - System error or hardware failure occurs

10. When training completes or stops:
   - System saves a final checkpoint with all training state
   - Displays training summary (total epochs, final losses, training duration)
   - Indicates the best checkpoint (lowest validation loss)
   - Provides next steps (export to ONNX for inference)

11. If training is interrupted (crash, power loss, user stop):
   - User can resume training by specifying the last checkpoint
   - Training continues from the exact epoch where it stopped
   - No progress is lost (checkpoints are saved periodically)
   - User does not need to restart from scratch

### Transfer Learning (Fine-tuning from Base Model)

12. When starting from a base checkpoint (recommended approach):
   - User provides a pre-trained checkpoint (e.g., French voice model)
   - System loads the base model's learned acoustic patterns
   - Training focuses on adapting these patterns to Japanese phonemes
   - Convergence occurs much faster (10x to 50x speedup vs. training from scratch)
   - User observes intelligible speech in early epochs (rather than noise)

13. Base model compatibility:
   - The phoneme set size may differ (French has different phonemes than Japanese)
   - System adapts or reinitializes the phoneme embedding layer if needed
   - Acoustic model and vocoder components transfer directly
   - User benefits from pre-learned speech patterns even if phonemes differ

### Configuration Flexibility

14. Training parameters can be customized:
   - Batch size (larger = faster but requires more memory, typical: 16-32)
   - Learning rate (affects convergence speed, typical: 0.0001)
   - Maximum epochs (typical: 1000+ for high quality)
   - Checkpoint frequency (typical: every 5-10 epochs)
   - Validation split percentage (typical: 10%)
   - Early stopping patience (typical: 50 epochs without improvement)
   - Hardware selection (GPU, MPS, CPU)

15. The system uses sensible defaults:
   - User does not need to understand all parameters to start training
   - Default parameters are optimized for medium-quality voice with reasonable training time
   - User can override any parameter for advanced customization

### Output Artifacts

16. Training produces these outputs:
   - Checkpoint files (.ckpt) in the checkpoints directory
   - Training logs in the logs directory (text logs for debugging)
   - TensorBoard logs in lightning_logs directory (for visualization)
   - Sample audio files at milestone epochs (for quality assessment)
   - Training summary report (final losses, best checkpoint, training duration)

## Acceptance Criteria

### Training Initialization Success
- Training starts without errors when all prerequisites are met
- System correctly detects and uses GPU/MPS acceleration when available
- Base checkpoint (if provided) loads successfully
- Training configuration is validated before starting
- User receives clear error messages if prerequisites are missing

### Training Progress and Monitoring
- Training loss decreases consistently over epochs (model is learning)
- Real-time progress displays current epoch, losses, and estimated time
- Checkpoints are saved at the configured frequency
- TensorBoard can be opened and displays loss curves in real-time
- User can observe training without blocking the training process

### Interruption and Resumption
- Training can be stopped at any time without corrupting checkpoints
- User can resume training from any saved checkpoint
- Resumed training continues from the exact epoch where it stopped
- Optimizer state is preserved (learning rate, momentum, etc.)
- No manual intervention required beyond providing the checkpoint path

### Transfer Learning Effectiveness
- Training from a base checkpoint produces intelligible speech in early epochs (under 100)
- Training from scratch produces noise initially and requires 500+ epochs for intelligibility
- Transfer learning converges at least 10x faster than training from scratch
- Final quality is comparable or better when using transfer learning

### Validation and Quality Assessment
- Validation loss is computed and displayed alongside training loss
- Overfitting is detectable (training loss continues decreasing but validation loss increases)
- Sample audio files are generated at milestone epochs
- Samples demonstrate progressive improvement in pronunciation and naturalness
- User can listen to samples without interrupting training

### Hardware Flexibility
- Training works on GPU (CUDA, if available)
- Training works on Apple Silicon MPS (if on macOS with M1/M2/M3)
- Training works on CPU (as fallback, though much slower)
- System automatically selects the best available accelerator
- User can override automatic selection if needed

### Configuration Robustness
- Default training parameters work without user modification
- User can customize any parameter without breaking training
- Invalid configuration values are rejected with clear error messages
- Configuration is saved alongside checkpoints for reproducibility
- Training can be reproduced by using the same configuration and data

### Output Completeness
- At least one checkpoint is saved during training
- Training logs capture all important events (start, checkpoint saves, completion, errors)
- TensorBoard logs enable visual inspection of training progress
- Sample audio files demonstrate voice quality at different training stages
- Training summary report contains all relevant metrics

### Performance Expectations
- Training processes at least 1 batch per second on modern GPUs
- Training a 10-hour dataset reaches 100 epochs within 24 hours on GPU
- Memory usage does not exceed reasonable limits (16GB RAM, 8GB VRAM)
- Disk space for checkpoints grows predictably (each checkpoint ~500MB to 1GB)

## Out of Scope

### Not Included in This Feature
- Multi-speaker training (single speaker only in this story)
- Distributed training across multiple GPUs or machines
- Hyperparameter tuning automation (user manually selects parameters)
- Automatic quality assessment (user listens to samples manually)
- Automatic early stopping based on quality metrics (only loss-based early stopping)
- Model architecture modifications (uses standard Piper VITS architecture)
- Custom loss functions (uses Piper's default losses)
- Fine-grained control over model components (encoder, decoder, vocoder are bundled)
- Training analytics beyond TensorBoard (no custom dashboards)
- Cloud training integration (local training only)
- Pre-download of base checkpoints (user must obtain separately)
- Automatic checkpoint cleanup (old checkpoints remain until user deletes)

### Future Enhancements Not Covered
- Automatic selection of optimal hyperparameters
- Quality-based early stopping (stop when voice sounds "good enough")
- Multi-GPU data parallel training
- Training progress notifications (email, SMS)
- Checkpoint compression to save disk space
- Automatic base model recommendation based on target language
- Training cost estimation (time and compute resources)
- A/B comparison of different training runs

## Assumptions and Constraints

### Assumptions
1. The user has completed preprocessing (dataset.jsonl, config.json, audio_norm_stats.json exist)
2. The user has access to a machine with sufficient compute resources (at minimum, CPU; ideally GPU/MPS)
3. The user can wait hours to days for training to complete
4. The user has basic understanding of training concepts (epochs, loss, checkpoints)
5. The user can manually evaluate voice quality by listening to samples
6. A base checkpoint is available for transfer learning (or user accepts slower training from scratch)
7. The dataset is of sufficient quality (validated in previous phases)
8. The user has 20-50GB of available disk space for checkpoints and logs

### Constraints
1. Training time depends on hardware: GPU (fast), MPS (medium), CPU (very slow)
2. Training a 10-hour dataset from scratch may take 3-7 days on CPU, 1-2 days on GPU
3. Transfer learning requires a compatible base checkpoint (phoneme count may differ)
4. Memory usage is proportional to batch size (larger batch = more memory)
5. Checkpoint files are large (500MB to 1GB each)
6. Training cannot be paused and resumed within an epoch (must complete current epoch)
7. TensorBoard must be manually started in a separate process
8. Validation samples are deterministic but not configurable (system selects automatically)

### Technical Constraints
1. Must use Piper's official training pipeline (piper_train module)
2. Must use PyTorch for neural network training
3. Must use PyTorch Lightning for training orchestration
4. Must generate checkpoints compatible with Piper's export process
5. Configuration must match Piper's expected config.json format
6. Training must work on macOS, Linux, and Windows (cross-platform)

### Quality Constraints
1. Training loss must decrease consistently (if loss stagnates, training configuration is incorrect)
2. Validation loss must not diverge significantly from training loss (no severe overfitting)
3. Sample audio must be intelligible by 100 epochs when using transfer learning
4. Final model must produce recognizable Japanese speech (not gibberish or noise)
5. Checkpoints must be recoverable (no corrupted saves)

### Resource Constraints
1. Minimum hardware: 8GB RAM, 4 CPU cores, 10GB disk space
2. Recommended hardware: 16GB RAM, GPU with 8GB VRAM, 50GB disk space
3. Training batch size limited by available memory
4. Number of checkpoints saved limited by available disk space

## Implementation Status

**REAL** - This is core functionality required for the Japanese voice training pipeline. Model training is the culminating step that produces the actual usable voice model. Without training, all previous preparation work has no output.

## Related Stories

- **STORY-001**: Overall Japanese voice vision (defines training goals and quality expectations)
- **STORY-002**: JSUT corpus infrastructure (provides audio data for training)
- **STORY-003**: Japanese phonetization (provides phoneme representations for training)
- **STORY-004**: Piper preprocessing (provides training-ready dataset.jsonl, config.json, audio_norm_stats.json)
- **STORY-006**: ONNX export and voice deployment (uses trained checkpoints) [Future]
- **STORY-007**: Voice quality validation (evaluates trained model) [Future]

## Success Metrics

This training feature is successful when:

1. User can start training with a single command
2. Training progresses without manual intervention
3. Loss curves show consistent learning (decreasing trend)
4. Training can be interrupted and resumed without data loss
5. Checkpoints are saved reliably and can be loaded
6. Sample audio demonstrates progressive quality improvement
7. Training completes and produces a final checkpoint ready for export
8. User can monitor training progress via TensorBoard
9. Transfer learning from base checkpoint accelerates training observably
10. The trained model (when exported) produces intelligible Japanese speech

### Quantitative Success Indicators
- Training reaches 100 epochs within 24 hours on GPU (for 10-hour dataset)
- Training loss decreases by at least 50% within first 100 epochs (transfer learning)
- Validation loss tracks within 20% of training loss (no severe overfitting)
- At least 5 checkpoints are saved during a typical training run
- Resume from checkpoint restarts within 1 minute

## User Workflow

### Expected User Experience (Transfer Learning - Recommended)

1. User has completed preprocessing (dataset.jsonl, config.json ready)
2. User obtains a base checkpoint (e.g., downloads French voice checkpoint from Piper repository)
3. User runs training command:
   ```
   python -m piper_train \
     --dataset-dir ./training \
     --resume_from_checkpoint ./checkpoints/fr_FR-siwis-medium.ckpt \
     --accelerator gpu \
     --batch-size 32 \
     --max_epochs 1000 \
     --checkpoint-epochs 10
   ```
4. System displays: "Initializing training from base checkpoint..."
5. System validates dataset and checkpoint compatibility
6. Training begins: "Starting training on GPU. Epoch 1/1000..."
7. User observes progress in terminal (epoch updates, loss decreasing)
8. User opens TensorBoard in another terminal: `tensorboard --logdir ./lightning_logs`
9. User inspects loss curves in browser (http://localhost:6006)
10. Training proceeds automatically, saving checkpoints every 10 epochs
11. User listens to sample audio files generated at epochs 50, 100, 150, etc.
12. After 200-300 epochs, user decides voice quality is sufficient
13. User stops training (Ctrl+C) and system saves final checkpoint
14. User receives confirmation: "Training stopped. Best checkpoint: epoch_280.ckpt"
15. User proceeds to export the checkpoint to ONNX format (next phase)

### Expected User Experience (Training from Scratch - Not Recommended)

1. User has preprocessed dataset but no base checkpoint
2. User runs training command without `--resume_from_checkpoint`
3. System displays: "Initializing training from random weights..."
4. Training begins but progress is very slow
5. First 100 epochs produce unintelligible noise (model is learning from scratch)
6. User waits patiently for 500+ epochs
7. Around epoch 500-800, speech becomes intelligible
8. Training takes 3-7 days to reach acceptable quality
9. User realizes transfer learning would have been much faster
10. User eventually obtains a trained model but at high time cost

### Interruption and Resumption Scenario

1. User is training (currently at epoch 150/1000)
2. Power failure or system crash occurs
3. User restarts the machine
4. User runs training command with resume checkpoint:
   ```
   python -m piper_train \
     --dataset-dir ./training \
     --resume_from_checkpoint ./lightning_logs/version_0/checkpoints/epoch=140.ckpt \
     --accelerator gpu \
     --batch-size 32 \
     --max_epochs 1000 \
     --checkpoint-epochs 10
   ```
5. System displays: "Resuming training from epoch 140..."
6. Training continues from epoch 141 as if nothing happened
7. User has lost minimal progress (only epochs 141-149, since last checkpoint was at 140)
8. Training proceeds normally to completion

### Error Scenario: Missing Prerequisites

1. User attempts to start training
2. System detects dataset.jsonl is missing
3. System displays: "Error: dataset.jsonl not found. Please run preprocessing first."
4. System lists missing files and expected locations
5. User runs preprocessing to generate required files
6. User retries training successfully

### Error Scenario: Out of Memory

1. User starts training with batch_size=64 on a GPU with limited VRAM
2. Training begins but crashes: "CUDA out of memory error"
3. System displays: "Error: Insufficient GPU memory. Try reducing --batch-size"
4. User reduces batch size to 32 and retries
5. Training proceeds successfully with smaller batch size

## User Value

This training integration enables:

- Creation of a working Japanese TTS voice model from prepared data
- Confidence that training is progressing correctly (loss monitoring)
- Resilience against interruptions (checkpoint resume capability)
- Dramatically faster training through transfer learning (10x speedup)
- Visual insight into training dynamics (TensorBoard integration)
- Experimentation with training parameters to optimize quality vs. time
- Reproducibility of training results (configuration saved with checkpoints)
- Foundation for contributing a Japanese voice to the Piper open source community

The end result is a trained model checkpoint ready for export to ONNX format, which can then be used with the Piper TTS command-line tool to synthesize Japanese speech from text. This checkpoint represents the culmination of all dataset preparation work and is the primary deliverable of the entire training pipeline.

Without reliable training integration, the extensive work of corpus acquisition, phonetization, and preprocessing would have no output. This story represents the critical bridge from prepared data to usable voice model.
