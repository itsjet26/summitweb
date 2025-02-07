#!/bin/bash

cd /workspace

wget -O RVC1006Nvidia.7z "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/RVC1006Nvidia.7z"
7z x RVC1006Nvidia.7z -oRVC
rm RVC1006Nvidia.7z

echo "✅ RVC Installed in /workspace/RVC"
