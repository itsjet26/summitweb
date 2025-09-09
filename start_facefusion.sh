#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh


#############################################
# Start VidGen
#############################################
echo "🚀 Starting VidGen..."
conda activate latentsync  # Assuming VidGen uses the same environment; change if needed.
cd /workspace/vidgen
nohup python -u generator.py > /workspace/vidgen.log 2>&1 & disown
echo "✅ VidGen started."
conda deactivate

echo "🚀 File Explorer..."
conda activate latentsync  # Assuming VidGen uses the same environment; change if needed.
cd /workspace/vidgen
nohup python -u files.py > /workspace/files.log 2>&1 & disown
echo "✅ File Explorer started."
conda deactivate

#############################################
# Start LatentSync
#############################################
echo "🚀 Starting LatentSync..."
conda activate latentsync
cd /workspace/LatentSync
nohup python -u gradio_app.py > /workspace/latentsync.log 2>&1 & disown
echo "✅ LatentSync started."

echo "🚀 Starting Overlayer..."
cd /workspace/overlayer
nohup python -u app.py > /workspace/overlayer.log 2>&1 & disown
echo "✅ Overlayer started."

echo "🚀 Starting Remixer..."
cd /workspace/Remixer
nohup python -u app.py > /workspace/remixer.log 2>&1 & disown
echo "✅ Remixer started."

echo "🚀 Starting Test..."
cd /workspace/ters
nohup python -u app.py > /workspace/ters.log 2>&1 & disown
echo "✅ Test started."
conda deactivate

echo "✅ FaceFusion, VidGen, and LatentSync are running successfully!"


