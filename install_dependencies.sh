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

echo "🛠️ Installing CUDA & cuDNN Once in Base Conda Environment..."
conda install -n base conda-forge::cuda-runtime=12.6.3 conda-forge::cudnn=9.3.0.75 -y

echo "🛠️ Setting up Conda environments..."

cd /workspace

echo "🐍 Creating Conda environment for FaceFusion..."
conda create --name facefusion python=3.12 -y
conda activate facefusion
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/facefusion/facefusion.git
cd facefusion
pip install --upgrade pip
pip install -r requirements.txt
pip install onnxruntime-gpu
python install.py --onnxruntime cuda
sed -i "s/ui.launch(favicon_path/ui.launch(show_api=False, share=True, favicon_path/" facefusion/uis/layouts/default.py
conda deactivate

cd /workspace

echo "🎥 Creating Conda environment for Video-Retalking..."
conda create -n video_retalking python=3.11 -y
conda activate video_retalking
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/vinthony/video-retalking.git
cp /summitweb/requirements.txt /workspace/video-retalking/requirements.txt
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

conda deactivate

echo "✅ Installation Complete! Now run 'install_rvc.sh' before starting programs."
