#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh
conda activate video_retalking

cd /workspace/video-retalking

# Start the Web UI
echo "🚀 Starting Video-Retalker Web UI..."
python -u video_retalker_ui.py 2>&1 | tee /workspace/video_retalker_ui.log &

sleep 10  # Allow Gradio to initialize

# Debug: Show logs
echo "🔍 Checking logs..."
tail -n 20 /workspace/video_retalker_ui.log

# Capture Gradio URL properly
GRADIO_URL=$(grep -oP 'Running on (http|https)://[^\s]+' /workspace/video_retalker_ui.log | tail -1 | awk '{print $3}')

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > /workspace/video_retalker_url.txt
    echo "✅ Video-Retalker Public URL: $GRADIO_URL"
else
    echo "❌ Failed to get Video-Retalker Gradio URL. Falling back to localhost." > /workspace/video_retalker_url.txt
fi

wait
