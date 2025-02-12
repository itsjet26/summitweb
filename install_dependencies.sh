#!/bin/bash

apt update
apt install -y git-all curl ffmpeg wget openssh-server p7zip-full cmake build-essential python3-opencv

mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh/authorized_keys
service ssh start

curl -LO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
rm Miniconda3-latest-Linux-x86_64.sh

export PATH="$HOME/miniconda/bin:$PATH"
source $HOME/miniconda/etc/profile.d/conda.sh
conda init
source ~/.bashrc

apt install -y cuda-toolkit-12-4
apt install -y libcudnn9-cuda-12 libcudnn9-dev-cuda-12

echo "export PATH=/usr/local/cuda/bin:\$PATH" >> ~/.bashrc
echo "export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\$LD_LIBRARY_PATH" >> ~/.bashrc
source ~/.bashrc

cd /workspace
conda create --name facefusion python=3.12 -y
conda activate facefusion
git clone https://github.com/facefusion/facefusion.git
cd facefusion
pip install --upgrade pip
pip install -r requirements.txt
pip install onnxruntime-gpu
python install.py --onnxruntime cuda
sed -i "s/ui.launch(favicon_path/ui.launch(show_api=False, share=True, favicon_path/" facefusion/uis/layouts/default.py
conda deactivate

cd /workspace
conda create -n video_retalking python=3.8 -y
conda activate video_retalking
git clone https://github.com/vinthony/video-retalking.git
cd video-retalking
conda install -y ffmpeg
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
sed -i "s/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/" /root/miniconda/envs/video_retalking/lib/python3.8/site-packages/basicsr/data/degradations.py

conda deactivate

echo "✅ Installation Complete! Now run 'install_rvc.sh' before starting programs."
