#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

# ========================
# 🎭 Start FaceFusion
# ========================
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

# ========================
# 🗣️ Start Video-Retalker
# ========================
conda activate video_retalking
cd /workspace/video-retalking

# Ensure Gradio is installed
pip install --upgrade gradio

# Start the Web UI in a fully detached background process
echo "🚀 Starting Video-Retalker Web UI..."
nohup python -u "/workspace/video-retalking/video_retalker_ui.py" > /workspace/video_retalker_ui.log 2>&1 & disown

# Wait for Gradio URL (retry for 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/facefusion.log | tail -1)
    
    if [[ -n "$GRADIO_URL" ]]; then
        echo "$GRADIO_URL" > /workspace/video_retalker_url.txt
        echo "✅ Video-Retalker Public URL: $GRADIO_URL"
        break
    fi
    
    ((timeout-=5))
done

if [[ -z "$GRADIO_URL" ]]; then
    echo "❌ Failed to get Video-Retalker Gradio URL. Falling back to localhost." > /workspace/video_retalker_url.txt
fi

# ========================
# 🎤 Start RVC
# ========================
cd /workspace/RVC1006Nvidia

# Run RVC Web UI
echo "🚀 Starting RVC..."
nohup /workspace/RVC1006Nvidia/runtime/python.exe infer-web.py --pycmd /workspace/RVC1006Nvidia/runtime/python.exe --port 7897 > /workspace/rvc.log 2>&1 & disown

sleep 20
echo "✅ RVC is running on http://localhost:7897"

# ========================
# 📊 Start Web Dashboard
# ========================
cd /workspace/summitweb

# Ensure Flask is installed
pip install flask

# Start the dashboard
echo "🚀 Starting Web Dashboard..."
nohup python web_dashboard.py > /workspace/web_dashboard.log 2>&1 & disown

echo "✅ All services started successfully!"

# Keep the container running
sleep infinity
