#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh
conda activate video_retalking

cd video-retalking
python video_retalker_ui.py 2>&1 | tee video_retalker_ui.log &

sleep 60

GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' video_retalker_ui.log | tail -1)

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > /workspace/video_retalker_url.txt
    echo "✅ Video-Retalker Public URL: $GRADIO_URL"
else
    echo "Failed to get Video-Retalker Gradio URL. Falling back to localhost." > video_retalker_url.txt
fi

wait
