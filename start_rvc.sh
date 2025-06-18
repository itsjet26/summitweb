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

#############################################
# Start Hunyuan
#############################################
echo "🚀 Starting Hunyuan..."
conda activate HunyuanVideo-Avatar
cd /workspace/HunyuanVideo-Avatar
#!/bin/bash
JOBS_DIR=$(dirname $(dirname "$0"))
export PYTHONPATH=./

export MODEL_BASE=./weights

checkpoint_path=${MODEL_BASE}/ckpts/hunyuan-video-t2v-720p/transformers/mp_rank_00_model_states.pt

# Add the environment variable here
TORCHELASTIC_ENABLE_FILE_LOGGING=1 torchrun \
    --nnodes=1 \
    --nproc_per_node=8 \
    --master_port 29605 \
    hymm_gradio/flask_audio.py \
    --input 'assets/test.csv' \
    --ckpt ${checkpoint_path} \
    --sample-n-frames 129 \
    --seed 128 \
    --image-size 704 \
    --cfg-scale 7.5 \
    --infer-steps 50 \
    --use-deepcache 1 \
    --flow-shift-eval-video 5.0 &

python3 hymm_gradio/gradio_audio.py

echo "✅ HunyuanVideo-Avatar started."
conda deactivate

echo "✅ FaceFusion, VidGen, and LatentSync are running successfully!"
