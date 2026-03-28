#!/bin/bash
# Download JSUT (Japanese Speech corpus) dataset
#
# JSUT is a free Japanese speech corpus containing ~7,300 utterances
# from a single female speaker.
#
# Citation:
# Ryosuke Sonobe, Shinnosuke Takamichi and Hiroshi Saruwatari,
# "JSUT corpus: free large-scale Japanese speech corpus for end-to-end speech synthesis,"
# arXiv preprint, 1711.00354, 2017.

set -e

echo "================================================================"
echo "Downloading JSUT Dataset"
echo "================================================================"

# Create dataset directory
DATASET_DIR="dataset/jsut"
mkdir -p "$DATASET_DIR"

echo "Target directory: $DATASET_DIR"
echo ""

# Download options
echo "Available JSUT subsets:"
echo "  1. basic5000 (5,000 sentences) - Recommended for quick start"
echo "  2. onomatopoeic5000 (5,000 onomatopoeic expressions)"
echo "  3. voiceactress100 (100 sentences with various emotions)"
echo "  4. all (complete dataset - ~10 GB)"
echo ""

read -p "Select option [1-4] (default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
  1)
    echo "Downloading basic5000..."
    SUBSET="basic5000"
    ;;
  2)
    echo "Downloading onomatopoeic5000..."
    SUBSET="onomatopoeic5000"
    ;;
  3)
    echo "Downloading voiceactress100..."
    SUBSET="voiceactress100"
    ;;
  4)
    echo "Downloading complete JSUT dataset..."
    SUBSET="all"
    ;;
  *)
    echo "Invalid option. Downloading basic5000 by default."
    SUBSET="basic5000"
    ;;
esac

echo ""
echo "Downloading JSUT corpus..."

cd "$DATASET_DIR"

# Download JSUT
# Note: JSUT corpus is hosted on Google Sites, not GitHub
# Alternative URLs if primary fails:
# - https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut_ver1.1.zip
# - http://ss-takashi.sakura.ne.jp/corpus/jsut_ver1.1.zip
wget http://ss-takashi.sakura.ne.jp/corpus/jsut_ver1.1.zip -O jsut.zip

echo "Extracting..."
unzip -q jsut.zip

# Move files
mv jsut_ver1.1/* .
rm -rf jsut_ver1.1
rm jsut.zip

echo ""
echo "================================================================"
echo "Download Complete!"
echo "================================================================"

if [ "$SUBSET" = "all" ]; then
  echo "Dataset location: $DATASET_DIR"
  echo ""
  echo "Available subsets:"
  ls -d */ 2>/dev/null | sed 's|/||'
else
  echo "Dataset location: $DATASET_DIR/$SUBSET"
fi

echo ""
echo "Dataset statistics:"
if [ -d "basic5000" ]; then
  BASIC_COUNT=$(find basic5000/wav -name "*.wav" 2>/dev/null | wc -l)
  echo "  - basic5000: $BASIC_COUNT audio files"
fi
if [ -d "onomatopoeic5000" ]; then
  ONOMA_COUNT=$(find onomatopoeic5000/wav -name "*.wav" 2>/dev/null | wc -l)
  echo "  - onomatopoeic5000: $ONOMA_COUNT audio files"
fi
if [ -d "voiceactress100" ]; then
  VOICE_COUNT=$(find voiceactress100/wav -name "*.wav" 2>/dev/null | wc -l)
  echo "  - voiceactress100: $VOICE_COUNT audio files"
fi

echo ""
echo "Next step: Prepare the dataset"
echo ""
echo "  python scripts/prepare_jsut_dataset.py \\"
echo "    --jsut-dir $DATASET_DIR/basic5000 \\"
echo "    --output-dir dataset/prepared \\"
echo "    --sample-rate 22050"
echo ""
