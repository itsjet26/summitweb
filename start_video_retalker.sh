#!/bin/bash
conda activate video_retalking
cd video-retalking

python video_retalker_ui.py 2>&1 | tee video_retalker_ui.log &

sleep 60

GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' video_retalker_ui.log | tail -1)

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > video_retalker_url.txt
else
    echo "Failed to get Video-Retalker URL"
fi

wait
