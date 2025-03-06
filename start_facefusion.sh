#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

#############################################
# Start FaceFusion
#############################################
echo "🚀 Starting FaceFusion..."
conda activate facefusion
cd /workspace/facefusion
nohup python -u facefusion.py run > /workspace/facefusion.log 2>&1 & disown
echo "✅ FaceFusion started."
conda deactivate

#############################################
# Start VidGen
#############################################
echo "🚀 Starting VidGen..."
conda activate facefusion  # Assuming VidGen uses the same environment; change if needed.
cd /workspace/vidgen
nohup python -u generator.py > /workspace/vidgen.log 2>&1 & disown
echo "✅ VidGen started."
conda deactivate

echo "🚀 File Explorer..."
conda activate facefusion  # Assuming VidGen uses the same environment; change if needed.
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
conda deactivate

echo "✅ FaceFusion, VidGen, and LatentSync are running successfully!"
