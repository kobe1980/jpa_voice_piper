@echo off
REM ============================================================================
REM Script de setup complet pour Windows
REM Etapes 1-5: Installation + Preparation dataset
REM ============================================================================

echo ============================================================================
echo   Setup Piper TTS Training - Windows
echo ============================================================================
echo.

REM Verification Python
echo [1/5] Verification Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo.
    echo Telechargez Python 3.11+ depuis: https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation
    pause
    exit /b 1
)
python --version
echo.

REM Verification GPU NVIDIA
echo [2/5] Verification GPU NVIDIA...
nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ATTENTION: nvidia-smi non disponible
    echo Le training sera TRES LENT sur CPU
    echo.
    echo Si vous avez un GPU NVIDIA, installez les drivers:
    echo https://www.nvidia.com/Download/index.aspx
    echo.
    pause
) else (
    echo GPU NVIDIA detecte:
    nvidia-smi --query-gpu=name --format=csv,noheader
    echo.
)

REM Installation PyTorch avec CUDA
echo [3/5] Installation PyTorch avec support GPU...
echo.
echo Quelle version CUDA voulez-vous?
echo   1. CUDA 11.8 (recommande, compatible RTX 20/30/40 series)
echo   2. CUDA 12.1 (plus recent, RTX 40 series)
echo   3. CPU seulement (TRES LENT, pas recommande)
echo.
choice /C 123 /N /M "Votre choix [1/2/3]: "

if errorlevel 3 (
    echo Installation PyTorch CPU...
    pip install torch torchvision torchaudio
) else if errorlevel 2 (
    echo Installation PyTorch CUDA 12.1...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
) else (
    echo Installation PyTorch CUDA 11.8...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
)

if %ERRORLEVEL% neq 0 (
    echo ERREUR: Installation PyTorch echouee
    pause
    exit /b 1
)
echo.

REM Installation Piper Training et dependances
echo [4/5] Installation Piper Training et dependances...
pip install piper-tts[training] soundfile librosa pykakasi tensorboard

if %ERRORLEVEL% neq 0 (
    echo ERREUR: Installation dependances echouee
    pause
    exit /b 1
)
echo.

REM Verification dataset
echo [5/5] Verification dataset...
echo.

if not exist "dataset\prepared\metadata_phonemes.csv" (
    echo ERREUR: Dataset non trouve dans dataset\prepared\
    echo.
    echo Le dataset devrait etre inclus dans le repo Git.
    echo Verifiez que vous avez bien fait: git pull
    echo.
    pause
    exit /b 1
)

REM Compter samples
for /f %%A in ('type "dataset\prepared\metadata_phonemes.csv" ^| find /c /v ""') do set sample_count=%%A
echo Dataset trouve: %sample_count% samples
echo.

if not exist "dataset\prepared\phoneme_map.json" (
    echo ERREUR: phoneme_map.json manquant
    pause
    exit /b 1
)
echo Phoneme map: OK
echo.

if not exist "dataset\prepared\wav" (
    echo ERREUR: Repertoire audio manquant
    pause
    exit /b 1
)
for /f %%A in ('dir /b "dataset\prepared\wav\*.wav" ^| find /c /v ""') do set wav_count=%%A
echo Fichiers audio: %wav_count% fichiers WAV
echo.

REM Validation environnement
echo Validation finale de l'environnement...
python scripts\validate_environment.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERREUR: Validation environnement echouee
    echo Verifiez les erreurs ci-dessus
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   Setup Complete!
echo ============================================================================
echo.
echo L'environnement est pret pour le training.
echo.
echo Prochaine etape:
echo   Lancer le training avec: train_windows.bat
echo.
echo Ou manuellement:
echo   python scripts\train_japanese_voice.py
echo.
pause
