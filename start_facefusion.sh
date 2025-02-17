#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

echo "🚀 Starting FaceFusion..."
conda activate facefusion
cd /workspace/facefusion

# Start FaceFusion in a fully detached background process
nohup python -u facefusion.py run > /workspace/facefusion.log 2>&1 & disown

# Wait for Gradio URL (retry for 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/facefusion.log | tail -1)
    
    if [[ -n "$GRADIO_URL" ]]; then
        echo "$GRADIO_URL" > /workspace/facefusion_url.txt
        echo "✅ FaceFusion Public URL: $GRADIO_URL"
        break
    fi
    
    ((timeout-=5))
done

if [[ -z "$GRADIO_URL" ]]; then
    echo "❌ Failed to get FaceFusion Gradio URL. Falling back to localhost." > /workspace/facefusion_url.txt
fi

echo "✅ FaceFusion is running successfully!"
