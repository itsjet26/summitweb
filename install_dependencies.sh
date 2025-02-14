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


echo "🛠️ Setting up Conda environments..."

cd /workspace

echo "🐍 Creating Conda environment for FaceFusion..."
conda create --name facefusion python=3.12 -y
conda activate facefusion
conda install -n facefusion conda-forge::cuda-runtime=12.6.3 conda-forge::cudnn=9.3.0.75 -y
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
conda create -n video_retalking python=3.8 -y
conda activate video_retalking
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
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

# 1️⃣ Remove any existing OpenCV installations (Conda & Pip)
conda remove --force opencv -y
pip uninstall opencv-python opencv-python-headless opencv-contrib-python -y

# 2️⃣ Install required dependencies
apt update
apt install -y build-essential cmake git pkg-config libgtk-3-dev \
               libjpeg-dev libpng-dev libtiff-dev libavcodec-dev \
               libavformat-dev libswscale-dev libv4l-dev ffmpeg libcanberra-gtk3-module

# 3️⃣ Clone OpenCV source code
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

# 4️⃣ Create build directory
cd opencv
mkdir build && cd build

# 5️⃣ Configure CMake with CUDA for RTX 4090 (`sm_90`)
cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D WITH_CUDA=ON \
      -D CUDA_ARCH_BIN="90" \
      -D WITH_CUDNN=ON \
      -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib/modules \
      -D WITH_TBB=ON \
      -D ENABLE_FAST_MATH=1 \
      -D CUDA_FAST_MATH=1 \
      -D WITH_OPENGL=ON \
      -D OPENCV_GENERATE_PKGCONFIG=ON ..

# 6️⃣ Compile OpenCV with CUDA (this step takes time)
make -j$(nproc)

# 7️⃣ Install OpenCV
make install


sed -i "s/from torchvision.transforms.functional_tensor import rgb_to_grayscale/from torchvision.transforms.functional import rgb_to_grayscale/" $HOME/miniconda/envs/video_retalking/lib/python3.8/site-packages/basicsr/data/degradations.py

conda deactivate

echo "✅ Installation Complete! Now run 'install_rvc.sh' before starting programs."
