#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh
conda activate facefusion

cd /workspace/facefusion
python -u facefusion.py run 2>&1 | tee /workspace/facefusion.log &

sleep 60

GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/facefusion.log | tail -1)

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > /workspaace/facefusion_url.txt
    echo "✅ FaceFusion Public URL: $GRADIO_URL"
else
    echo "Failed to get FaceFusion Gradio URL. Falling back to localhost." > /workspace/facefusion_url.txt
fi

wait
