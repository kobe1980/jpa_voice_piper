#!/bin/bash
# Script pour créer le package de transfert

echo "📦 Creating transfer package..."
echo ""

# Créer archive avec compression
tar -czf ../jpa_voice_piper_transfer.tar.gz \
  --exclude=".git" \
  --exclude="lightning_logs" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude=".venv" \
  --exclude="node_modules" \
  --exclude="piper-training/.git" \
  --exclude="*.ckpt" \
  --exclude="test_*.wav" \
  --exclude="demo_outputs" \
  dataset/prepared/ \
  dataset/jsut/basic5000/transcript_utf8.txt \
  scripts/*.py \
  scripts/*.sh \
  scripts/download_jsut.sh \
  scripts/prepare_jsut_dataset.py \
  piper_voice/ \
  tests/ \
  pyproject.toml \
  uv.lock \
  README.md \
  CLAUDE.md \
  TRAINING_ON_WINDOWS_GPU.md \
  TRAINING_FAILURE_REPORT.md \
  SUMMARY_AND_NEXT_STEPS.md \
  TRANSFER_PACKAGE_README.md

echo ""
echo "✅ Package created: ../jpa_voice_piper_transfer.tar.gz"
echo ""

# Afficher taille
SIZE=$(du -h ../jpa_voice_piper_transfer.tar.gz | cut -f1)
echo "📊 Size: $SIZE"
echo ""

echo "📝 Contents:"
tar -tzf ../jpa_voice_piper_transfer.tar.gz | head -20
echo "   ... (and more)"
echo ""

echo "✅ Ready for transfer to Windows/Linux machine!"
