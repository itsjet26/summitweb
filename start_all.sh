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
export TORCH_CUDA_ARCH_LIST="8.9+PTX"
export CUDA_HOME=/usr/local/cuda
cd /workspace/video-retalking


# Start the Web UI in a fully detached background process
echo "🚀 Starting Video-Retalker Web UI..."

nohup python -u /workspace/video-retalking/webUI.py > /workspace/video_retalker_ui.log 2>&1 & disown

# Wait for Gradio URL (retry for 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/video_retalker_ui.log | tail -1)
    
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
#!/bin/bash

# Navigate to the RVC folder
cd /workspace/RVC1006Nvidia

apt update && apt install -y aria2
chmod +x ./tools/*.sh
# Ensure the script is executable
chmod +x run.sh

# Run the script in the background and log output
nohup ./run.sh > /workspace/rvc.log 2>&1 & disown

# Wait a few seconds for the process to initialize
sleep 90

# Check for the Gradio URL in logs
GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/rvc.log | tail -1)

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > /workspace/rvc_url.txt
    echo "✅ RVC Public URL: $GRADIO_URL"
else
    echo "❌ Failed to get RVC Gradio URL. Falling back to localhost." > /workspace/rvc_url.txt
fi


# ========================
# 📊 Start Web Dashboard
# ========================
cd /summitweb

# Ensure Flask is installed
pip install flask

# Start the dashboard
echo "🚀 Starting Web Dashboard..."
nohup python web_dashboard.py > /workspace/web_dashboard.log 2>&1 & disown

echo "✅ All services started successfully!"

# Keep the container running
sleep infinity
