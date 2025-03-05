#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

#############################################
# Start FaceFusion
#############################################
echo "🚀 Starting FaceFusion..."
conda activate wan2.1
cd /workspace/Wan2.1/gradio

# Start FaceFusion in a fully detached background process
nohup python -u t2v_14B_singleGPU.py --prompt_extend_method 'local_qwen' --ckpt_dir ./Wan2.1-T2V-14B > /workspace/wan.log 2>&1 & disown

# Wait for Gradio URL (retry for up to 90 seconds)
timeout=90
while [[ $timeout -gt 0 ]]; do
    sleep 5
    FF_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/wan.log | tail -1)
    if [[ -n "$FF_URL" ]]; then
        echo "$FF_URL" > /workspace/wan_url.txt
        echo "✅ FaceFusion Public URL: $FF_URL"
        break
    fi
    ((timeout-=5))
done

if [[ -z "$FF_URL" ]]; then
    echo "❌ Failed to get FaceFusion Gradio URL. Falling back to localhost." > /workspace/wan_url.txt
fi
