#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh
conda activate video_retalking

cd /workspace/video-retalking

# Start the Web UI in a fully detached background process
echo "🚀 Starting Video-Retalker Web UI..."
nohup python -u "/summitweb/video_retalker_ui.py" > /workspace/video_retalker_ui.log 2>&1 & disown

# Wait for Gradio URL (retry for 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    GRADIO_URL=$(grep -oP 'Running on (http|https)://[^\s]+' /workspace/video_retalker_ui.log | tail -1 | awk '{print $2}')
    
    if [[ -n "$GRADIO_URL" ]]; then
        echo "$GRADIO_URL" > /workspace/video_retalker_url.txt
        echo "✅ Video-Retalker Public URL: $GRADIO_URL"
        break
    fi
    
    ((timeout-=5))
done

# If no URL was found, fallback to localhost
if [[ -z "$GRADIO_URL" ]]; then
    echo "❌ Failed to get Video-Retalker Gradio URL. Falling back to localhost." > /workspace/video_retalker_url.txt
fi
