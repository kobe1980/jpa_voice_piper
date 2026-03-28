@echo off
REM ============================================================================
REM Script de training pour Windows
REM Lance l'entrainement avec detection automatique GPU
REM ============================================================================

echo ============================================================================
echo   Piper TTS Training - Japanese Voice
echo ============================================================================
echo.

REM Verification que le setup a ete fait
if not exist "dataset\prepared\metadata_phonemes.csv" (
    echo ERREUR: Dataset non trouve!
    echo.
    echo Avez-vous lance setup_windows.bat d'abord?
    echo.
    pause
    exit /b 1
)

REM Verification Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERREUR: Python non trouve
    echo Lancez setup_windows.bat d'abord
    pause
    exit /b 1
)

echo Dataset: OK
echo Python: OK
echo.

REM Detection GPU
nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ATTENTION: Aucun GPU NVIDIA detecte
    echo Le training sera TRES LENT sur CPU (3-7 jours)
    echo.
    echo Voulez-vous continuer quand meme? [O/N]
    choice /C ON /N /M "Votre choix: "
    if errorlevel 2 (
        echo Training annule
        pause
        exit /b 0
    )
    set ACCELERATOR=cpu
) else (
    echo GPU NVIDIA detecte:
    nvidia-smi --query-gpu=name --format=csv,noheader
    echo.
    set ACCELERATOR=gpu
)

echo ============================================================================
echo   Lancement du Training
echo ============================================================================
echo.
echo Accelerateur: %ACCELERATOR%
echo.

if "%ACCELERATOR%"=="gpu" (
    echo Duree estimee: 6-12 heures
) else (
    echo Duree estimee: 3-7 JOURS
)
echo.

echo Appuyez sur une touche pour demarrer le training...
echo Ou CTRL+C pour annuler
pause >nul
echo.

REM Lancer training avec script Python
python scripts\train_japanese_voice.py --accelerator %ACCELERATOR%

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================================
    echo   ERREUR: Training echoue
    echo ============================================================================
    echo.
    echo Verifiez les logs ci-dessus
    echo.
) else (
    echo.
    echo ============================================================================
    echo   Training Complete!
    echo ============================================================================
    echo.
    echo Prochaines etapes:
    echo   1. Trouver le meilleur checkpoint:
    echo      dir lightning_logs\version_*\checkpoints\*.ckpt
    echo.
    echo   2. Exporter vers ONNX:
    echo      python -m piper.train.export_onnx checkpoint.ckpt model.onnx
    echo.
    echo   3. Tester:
    echo      echo こんにちは ^| piper -m model.onnx -f test.wav
    echo.
)

pause
