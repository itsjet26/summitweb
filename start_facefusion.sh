#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

#############################################
# Start FaceFusion
#############################################
echo "🚀 Starting FaceFusion..."
conda activate facefusion
cd /workspace/facefusion

# Start FaceFusion in a fully detached background process
nohup python -u facefusion.py run > /workspace/facefusion.log 2>&1 & disown

# Wait for Gradio URL (retry for up to 90 seconds)
timeout=90
while [[ $timeout -gt 0 ]]; do
    sleep 5
    FF_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/facefusion.log | tail -1)
    if [[ -n "$FF_URL" ]]; then
        echo "$FF_URL" > /workspace/facefusion_url.txt
        echo "✅ FaceFusion Public URL: $FF_URL"
        break
    fi
    ((timeout-=5))
done

if [[ -z "$FF_URL" ]]; then
    echo "❌ Failed to get FaceFusion Gradio URL. Falling back to localhost." > /workspace/facefusion_url.txt
fi

echo "🚀 Starting FileExplorer..."
cd /workspace/vidgen
nohup python -u files.py > /workspace/files.log 2>&1 & disown

# Wait for VidGen Gradio URL (retry for up to 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    VIDGEN_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/files.log | tail -1)
    if [[ -n "$VIDGEN_URL" ]]; then
        echo "$VIDGEN_URL" > /workspace/files_url.txt
        echo "✅ VidGen Public URL: $VIDGEN_URL"
        break
    fi
    ((timeout-=5))
done

if [[ -z "$VIDGEN_URL" ]]; then
    echo "❌ Failed to get VidGen Gradio URL. Falling back to localhost." > /workspace/files_url.txt
fi

echo "🚀 Starting VidGen..."
cd /workspace/vidgen
nohup python -u generator.py > /workspace/vidgen.log 2>&1 & disown

# Wait for VidGen Gradio URL (retry for up to 60 seconds)
timeout=60
while [[ $timeout -gt 0 ]]; do
    sleep 5
    VIDGEN_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/vidgen.log | tail -1)
    if [[ -n "$VIDGEN_URL" ]]; then
        echo "$VIDGEN_URL" > /workspace/vidgen_url.txt
        echo "✅ VidGen Public URL: $VIDGEN_URL"
        break
    fi
    ((timeout-=5))
done

if [[ -z "$VIDGEN_URL" ]]; then
    echo "❌ Failed to get VidGen Gradio URL. Falling back to localhost." > /workspace/vidgen_url.txt
fi
conda deactivate
#############################################
# Start LatentSync
#############################################
echo "🚀 Starting LatentSync..."
# Activate the LatentSync environment (adjust the env name if needed)
conda activate latentsync
cd /workspace/LatentSync

# Launch the LatentSync Gradio app in a detached background process
nohup python -u gradio_app.py > /workspace/latentsync.log 2>&1 & disown

# Wait for LatentSync Gradio URL (retry for up to 90 seconds)
timeout=90
while [[ $timeout -gt 0 ]]; do
    sleep 5
    LS_URL=$(grep -oP 'Running on public URL: \K(https://.*)' /workspace/latentsync.log | tail -1)
    if [[ -n "$LS_URL" ]]; then
        echo "$LS_URL" > /workspace/latentsync_url.txt
        echo "✅ LatentSync Public URL: $LS_URL"
        break
    fi
    ((timeout-=5))
done

if [[ -z "$LS_URL" ]]; then
    echo "❌ Failed to get LatentSync Gradio URL. Falling back to localhost." > /workspace/latentsync_url.txt
fi
conda deactivate

echo "✅ FaceFusion, VidGen, and LatentSync are running successfully!"
