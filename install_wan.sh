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

echo "🐍 Creating Conda environment for WanAI..."
conda create -n wan2.1 python=3.11 -y
conda activate wan2.1

echo "🔨 Cloning Wan2.1 repository..."
git clone https://github.com/Wan-Video/Wan2.1.git
cd Wan2.1
pip install --upgrade pip
pip install -r requirements.txt
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.1-T2V-14B --local-dir ./Wan2.1-T2V-14B
pip install modelscope
modelscope download Wan-AI/Wan2.1-T2V-14B --local_dir ./Wan2.1-T2V-14B
sed -i 's/demo.launch(server_name="0.0.0.0", share=False, server_port=7860)/demo.launch(server_name="0.0.0.0", share=True, server_port=7860)/' gradio/t2v_14B_singleGPU.py
conda deactivate

echo "✅ Wan2.1 Installation Complete!"
