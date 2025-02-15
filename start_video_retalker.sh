#!/bin/bash

set -e  # Exit script if any command fails
set -o pipefail  # Fail pipeline if any command fails

echo "🚀 Updating and installing dependencies..."
apt update
apt install -y git-all curl ffmpeg wget openssh-server p7zip-full cmake build-essential python3-opencv

echo "🔑 Setting up SSH access..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
service ssh start

echo "📥 Installing Miniconda..."
curl -LO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
rm Miniconda3-latest-Linux-x86_64.sh

export PATH="$HOME/miniconda/bin:$PATH"
source $HOME/miniconda/etc/profile.d/conda.sh
conda init
source ~/.bashrc

cd /workspace

echo "🎥 Creating Conda environment for Video-Retalking..."
conda create -n video_retalking python=3.11 conda-forge::cuda-runtime=12.6.3 conda-forge::cudnn=9.3.0.75 -y
conda activate video_retalking
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/vinthony/video-retalking.git
cp /summitweb/webUI.py /workspace/video-retalking/webUI.py
cd video-retalking
conda install -y ffmpeg
conda install -c conda-forge dlib
pip install -r requirements.txt
pip install gdown

mkdir -p ./checkpoints
GDRIVE_FOLDER_ID="18rhjMpxK8LVVxf7PI6XwOidt8Vouv_H0"

echo "📥 Downloading checkpoints from Google Drive..."
gdown --folder "https://drive.google.com/drive/folders/$GDRIVE_FOLDER_ID" -O ./checkpoints

if [[ "$(ls -A ./checkpoints)" ]]; then
    echo "✅ All required checkpoint files have been downloaded successfully."
else
    echo "❌ Failed to download checkpoint files. Please check your Google Drive link or permissions."
    exit 1
fi

sed -i "s/demo.queue().launch()/demo.queue().launch(share=True)/" webUI.py
sed -i "s/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/" $HOME/miniconda/envs/video_retalking/lib/python3.11/site-packages/basicsr/data/degradations.py


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
