#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh
conda activate video_retalking

# Start the Web UI
echo "🚀 Starting Video-Retalker Web UI..."
python -u "/summitweb/video_retalker_ui.py" 2>&1 | tee video_retalker_ui.log &

sleep 10  # Allow Gradio to initialize

# Debug: Show logs
echo "🔍 Checking logs..."
tail -n 20 video_retalker_ui.log

# Capture Gradio URL properly
GRADIO_URL=$(grep -oP 'Running on (http|https)://[^\s]+' video_retalker_ui.log | tail -1 | awk '{print $3}')

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > video_retalker_url.txt
    echo "✅ Video-Retalker Public URL: $GRADIO_URL"
else
    echo "❌ Failed to get Video-Retalker Gradio URL. Falling back to localhost." > video_retalker_url.txt
fi

wait
