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

echo "🛠️ Setting up Conda environments..."

cd /workspace

echo "🐍 Creating Conda environment for FaceFusion..."
conda create --name facefusion python=3.12 -y
conda activate facefusion
conda install -n facefusion conda-forge::cuda-runtime=12.6.3 conda-forge::cudnn=9.3.0.75 -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

echo "🔨 Cloning FaceFusion repository..."
git clone https://github.com/facefusion/facefusion.git
cd facefusion
pip install --upgrade pip
pip install -r requirements.txt
pip install onnxruntime-gpu
python install.py --onnxruntime cuda
sed -i "s/ui.launch(favicon_path = 'facefusion.ico', inbrowser = state_manager.get_item('open_browser'))/ui.launch(server_name=\"0.0.0.0\", share=False, server_port=7860, favicon_path = 'facefusion.ico', inbrowser = state_manager.get_item('open_browser'))/" facefusion/uis/layouts/default.py
conda deactivate

echo "✅ FaceFusion Installation Complete!"

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

# OpenCV dependencies
apt -y install libgl1

# Download all the checkpoints from HuggingFace
huggingface-cli download ByteDance/LatentSync-1.5 whisper/tiny.pt --local-dir checkpoints
huggingface-cli download ByteDance/LatentSync-1.5 latentsync_unet.pt --local-dir checkpoints

echo "✅ LatentSync Setup Complete!"

# Change directory back to /workspace
cd /workspace

echo "🔨 Cloning Hunyuan repository..."
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar.git
cd HunyuanVideo-Avatar

echo "📥 Running LatentSync environment setup..."
# The setup_env.sh script sets up a conda environment and installs required packages.

#!/bin/bash

conda create -n HunyuanVideo-Avatar python==3.10.9
conda activate HunyuanVideo-Avatar
conda install pytorch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 pytorch-cuda=12.4 -c pytorch -c nvidia
python -m pip install -r requirements.txt
python -m pip install ninja
python -m pip install git+https://github.com/Dao-AILab/flash-attention.git@v2.6.3
pip install --force-reinstall pydantic==2.10.6
python -m pip install "huggingface_hub[cli]"
cd /workspace/HunyuanVideo-Avatar/weights
huggingface-cli download tencent/HunyuanVideo-Avatar --local-dir ./

echo "✅ LatentSync Setup Complete!"

#############################################
# Additional Steps: Download GDrive files and install Pillow
#############################################

# Change directory to /workspace to prepare for the next steps
cd /workspace

# Activate the facefusion environment again
conda activate facefusion

# Install gdown (if not already installed) to download files from Google Drive
pip install gdown

# Download the files from the specified Google Drive folder.
# Replace <FOLDER_ID> with the folder id extracted from the URL.
# The folder id here is "19mSqb4FklllysWOOodunA_BEhMizRU72".
echo "📥 Downloading additional files from Google Drive..."
gdown --folder "https://drive.google.com/drive/folders/19mSqb4FklllysWOOodunA_BEhMizRU72?usp=drive_link"
sed -i "s/demo.launch(share=True)/demo.launch(server_name=\"0.0.0.0\", share=False, server_port=7862, inbrowser=True)/" vidgen/generator.py

# Install Pillow version 10.2.0
echo "📦 Installing Pillow==10.2.0..."
pip install pillow==10.2.0

conda deactivate

echo "🎉 Setup complete!"
