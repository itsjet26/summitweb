#!/bin/bash

# Ensure Conda is initialized
source ~/miniconda/etc/profile.d/conda.sh

#############################################
# Install and Configure Nginx
#############################################
echo "🚀 Installing and configuring Nginx..."
# Update package list and install Nginx (if not installed)
if ! command -v nginx &> /dev/null; then
    apt-get update && apt-get install -y nginx
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Nginx. Exiting."
        exit 1
    fi
fi

# Ensure /workspace exists for persistent files
mkdir -p /workspace
chmod -R u+w /workspace  # Make writable

# Remove any invalid PID files
sudo rm -f /run/nginx.pid /workspace/nginx.pid

# Create or update Nginx configuration with persistent PID and correct ports
cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
pid /workspace/nginx.pid;  # Persistent PID location

events {
    worker_connections 768;
}

http {
    client_max_body_size 1024M;  # Allow large requests (e.g., videos, models)
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 8080;  # Use an unused port (not 7860-7862)
        server_name _;

        location / {
            proxy_pass http://localhost:7860;  # FaceFusion
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            client_max_body_size 1024M;
        }

        location /vidgen/ {
            proxy_pass http://localhost:7861;  # VidGen
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            client_max_body_size 1024M;
        }

        location /latentsync/ {
            proxy_pass http://localhost:7862;  # LatentSync
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            client_max_body_size 1024M;
        }
    }
}
EOF

# Test Nginx configuration
nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration error. Check /etc/nginx/nginx.conf and logs."
    tail -f /var/log/nginx/error.log
    exit 1
fi

#############################################
# Start FaceFusion
#############################################
echo "🚀 Starting FaceFusion..."
conda activate facefusion
cd /workspace/facefusion

# Start FaceFusion on port 7860 in a detached background process
nohup python -u facefusion.py run --server-port 7860 > /workspace/facefusion.log 2>&1 & disown

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

#############################################
# Start VidGen
#############################################
echo "🚀 Starting VidGen..."
cd /workspace/vidgen
nohup python -u generator.py --server-port 7861 > /workspace/vidgen.log 2>&1 & disown

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
conda activate latentsync
cd /workspace/LatentSync

# Launch the LatentSync Gradio app on port 7862 in a detached background process
nohup python -u gradio_app.py --server-port 7862 > /workspace/latentsync.log 2>&1 & disown

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

#############################################
# Start Nginx
#############################################
echo "🚀 Starting Nginx..."
# Start Nginx in foreground mode for stability in the container
nginx -g "daemon off;"  # Run in foreground, ensuring it stays running
echo "✅ Nginx started successfully, proxying to Gradio apps on ports 7860, 7861, 7862"

echo "✅ FaceFusion, VidGen, LatentSync, and Nginx are running successfully!"
