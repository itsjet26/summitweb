import random
import subprocess
import os
import gradio as gr
import shutil
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))
process = None  # Global variable to track the subprocess


def convert(video, audio):
    global process
    print("Received files:", video, audio)

    # Convert to absolute paths to avoid Gradio temp path issues
    video_path = os.path.abspath(video)
    audio_path = os.path.abspath(audio)

    # Ensure paths are properly formatted for Windows/Linux compatibility
    video_path = video_path.replace("\\", "/")
    audio_path = audio_path.replace("\\", "/")

    print("Processed file paths:", video_path, audio_path)

    output_file = f"results/output_{random.randint(0, 1000)}.mp4"

    # Process the video with the provided audio
    command = ["python3", "inference.py", "--face", video_path,
               "--audio", audio_path, "--outfile", output_file]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"  # Specify GPU

    process = subprocess.Popen(command, env=env)
    process.wait()

    # Cleanup temporary files
    temp_dir = os.path.join(current_dir, "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    return output_file


def stop_processing():
    global process
    if process and process.poll() is None:
        process.terminate()
        process = None
    return "Processing Stopped"


with gr.Blocks(
        title="Audio-based Lip Synchronization",
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.green,
            font=["Source Sans Pro", "Arial", "sans-serif"],
            font_mono=['JetBrains mono', "Consolas", 'Courier New']
        ),
) as demo:
    with gr.Row():
        gr.Markdown("# Audio-based Lip Synchronization")
    with gr.Row():
        with gr.Column():
            with gr.Row():
                v = gr.File(label='Source Face', file_types=['video'])
            with gr.Row():
                a = gr.File(label='Target Audio', file_types=['audio'])
            with gr.Row():
                btn = gr.Button(value="Synthesize", variant="primary")
                stop_btn = gr.Button(value="Stop", variant="stop")
        with gr.Column():
            o = gr.File(label="Output Video")

    btn.click(fn=convert, inputs=[v, a], outputs=[o])
    stop_btn.click(fn=stop_processing, inputs=[], outputs=[])

demo.queue().launch(share=True)
