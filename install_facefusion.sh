#!/bin/bash

set -e  # Exit script if any command fails
set -o pipefail  # Fail pipeline if any command fails

echo "🚀 Updating and installing dependencies..."
apt update
apt install -y git curl ffmpeg wget openssh-server p7zip-full cmake build-essential python3-opencv

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

# Accept Anaconda Terms of Service for required channels
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

echo "🛠️ Setting up Conda environments..."

#############################################
# Additional Steps for LatentSync
#############################################

# Change directory back to /workspace
cd /workspace

echo "🔨 Cloning LatentSync repository..."
git clone https://github.com/bytedance/LatentSync.git
cd LatentSync

echo "📥 Running LatentSync environment setup..."
# The setup_env.sh script sets up a conda environment and installs required packages.
cp /summitweb/gradio_app.py /workspace/LatentSync/gradio_app.py

#!/bin/bash

# Create a new conda environment
conda create -y -n latentsync python=3.10.13
conda activate latentsync

# Install ffmpeg
conda install -y -c conda-forge ffmpeg

# Python dependencies
pip install -r requirements.txt

pip install gdown
pip install flask --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib


# OpenCV dependencies
apt -y install libgl1

# Download all the checkpoints from HuggingFace
huggingface-cli download ByteDance/LatentSync-1.5 whisper/tiny.pt --local-dir checkpoints
huggingface-cli download ByteDance/LatentSync-1.5 latentsync_unet.pt --local-dir checkpoints

echo "✅ LatentSync Setup Complete!"

#############################################
# Additional Steps: Download GDrive files and install Pillow
#############################################

cd /workspace

gdown --folder "https://drive.google.com/drive/folders/1Y7rz5fo5DKI6UdQj9FruIVOROgIlpi7X?usp=drive_link"
gdown --folder "https://drive.google.com/drive/folders/1E9WazK7GsMivJhQhiokQGpfNp7xVi1gN?usp=drive_link"
gdown --folder "https://drive.google.com/drive/folders/1J9iXTjER0NsB-e9RaGRjOrn3ayO264t8?usp=drive_link"
echo "📥 Downloading additional files from Google Drive..."
gdown --folder "https://drive.google.com/drive/folders/19mSqb4FklllysWOOodunA_BEhMizRU72?usp=drive_link"
sed -i "s/demo.launch(share=True)/demo.launch(server_name=\"0.0.0.0\", share=False, server_port=7862, inbrowser=True)/" vidgen/generator.py

# Install Pillow version 10.2.0
echo "📦 Installing Pillow==10.2.0..."
pip install pillow==10.2.0

conda deactivate

echo "🎉 Setup complete!"
