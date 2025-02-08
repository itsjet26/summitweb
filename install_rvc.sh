#!/bin/bash

cd /workspace

wget -O RVC1006Nvidia.7z "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/RVC1006Nvidia.7z"
7z x RVC1006Nvidia.7z
rm RVC1006Nvidia.7z

cd /workspace/RVC1006Nvidia
sed -i 's/input_audio0 = gr.Textbox( *label=i18n("输入待处理音频文件路径(默认是正确格式示例)")/input_audio0 = gr.File(label="Upload Audio File", file_count="single")/g' infer-web.py
sed -i 's/input_face0 = gr.Textbox( *label=i18n("输入人脸图像路径")/input_face0 = gr.File(label="Upload Face Image", file_count="single")/g' infer-web.py
sed -i 's/i18n("单次推理")/"Single Inference"/g' infer-web.py
sed -i 's/i18n("伴奏人声分离&去混响&去回声")/"Vocal Separation & De-reverb & Echo Removal"/g' infer-web.py
sed -i 's/i18n("训练")/"Training"/g' infer-web.py
sed -i 's/i18n("ckpt处理")/"Checkpoint Processing"/g' infer-web.py
sed -i 's/i18n("Onnx导出")/"ONNX Export"/g' infer-web.py
sed -i 's/i18n("常见问题解答")/"FAQ"/g' infer-web.py
sed -i 's/output_path = gr.Textbox( *label=i18n("输出文件路径")/output_path = gr.File(label="Download Processed File", interactive=True)/g' infer-web.py
sed -i '/else:/,/quiet=True,/ s/.*app.queue.*/        app.queue(concurrency_count=511, max_size=1022).launch(share=True)/' infer-web.py

echo "✅ RVC Installed in /workspace/RVC1006Nvidia"
