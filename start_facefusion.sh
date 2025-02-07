#!/bin/bash
conda activate facefusion
cd facefusion
python -u facefusion.py run 2>&1 | tee facefusion.log &

sleep 60

GRADIO_URL=$(grep -oP 'Running on public URL: \K(https://.*)' facefusion.log | tail -1)

if [[ -n "$GRADIO_URL" ]]; then
    echo "$GRADIO_URL" > facefusion_url.txt
else
    echo "Failed to get FaceFusion URL"
fi

wait
