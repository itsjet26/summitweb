#!/bin/bash

cd /workspace

wget -O RVC1006Nvidia.7z "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/RVC1006Nvidia.7z"
7z x RVC1006Nvidia.7z
rm RVC1006Nvidia.7z

cd /workspace/RVC1006Nvidia

sed -i '/else:/,/quiet=True,/ s/.*app.queue.*/        app.queue(concurrency_count=511, max_size=1022).launch(share=True)/' /workspace/RVC1006Nvidia/infer-web.py

echo "✅ RVC Installed in /workspace/RVC1006Nvidia"
