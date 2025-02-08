#!/bin/bash

cd /workspace

wget -O RVC1006Nvidia.7z "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/RVC1006Nvidia.7z"
7z x -mmt=on RVC1006Nvidia.7z
rm RVC1006Nvidia.7z

cd /workspace/RVC1006Nvidia
# 1. Replace the tab label for single inference.
sed -i 's/i18n("单次推理")/"Single Inference"/g' infer-web.py

# 2. Replace the tab label for vocal separation & de-reverb & echo removal.
sed -i 's/i18n("伴奏人声分离&去混响&去回声")/"Vocal Separation & De-reverb & Echo Removal"/g' infer-web.py

# 3. Replace the label for training.
sed -i 's/i18n("训练")/"Training"/g' infer-web.py

# 4. Replace the label for checkpoint processing.
sed -i 's/i18n("ckpt处理")/"Checkpoint Processing"/g' infer-web.py

# 5. Replace the label for ONNX export.
sed -i 's/i18n("Onnx导出")/"ONNX Export"/g' infer-web.py

# 6. Replace the label for FAQ.
sed -i 's/i18n("常见问题解答")/"FAQ"/g' infer-web.py

# 7. Replace input label for audio file path.
sed -i 's/i18n("输入待处理音频文件路径(默认是正确格式示例)")/"Upload Audio File"/g' infer-web.py

# 8. Replace input label for face image path.
sed -i 's/i18n("输入人脸图像路径")/"Upload Face Image"/g' infer-web.py

# 9. Replace output label for file path.
sed -i 's/i18n("输出文件路径")/"Download Processed File"/g' infer-web.py

# 10. Replace label for refreshing speaker list and index paths.
sed -i 's/i18n("刷新音色列表和索引路径")/"Refresh Speaker List and Index Paths"/g' infer-web.py

# 11. Replace label for unloading speaker to save memory.
sed -i 's/i18n("卸载音色省显存")/"Unload Speaker to Save Memory"/g' infer-web.py

# 12. Replace label for "select speaker id".
sed -i 's/i18n("请选择说话人id")/"Select Speaker ID"/g' infer-web.py

# 13. Replace label for "转换" (Convert).
sed -i 's/i18n("转换")/"Convert"/g' infer-web.py

# 14. Replace label for "输出信息" (Output Info).
sed -i 's/i18n("输出信息")/"Output Info"/g' infer-web.py

# 15. Replace the tab label for batch inference.
sed -i 's/i18n("批量推理")/"Batch Inference"/g' infer-web.py

# 16. Replace any instance of "模型推理" with "Model Inference".
sed -i 's/i18n("模型推理")/"Model Inference"/g' infer-web.py

sed -i '/else:/,/quiet=True,/ s/.*app.queue.*/        app.queue(concurrency_count=511, max_size=1022).launch(share=True)/' infer-web.py

echo "✅ RVC Installed in /workspace/RVC1006Nvidia"
