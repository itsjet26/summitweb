import gradio as gr
import os
import subprocess

VIDEO_RETALKER_PATH = "/workspace/video-retalking"  # Adjust if installed elsewhere
CHECKPOINTS_PATH = os.path.join(VIDEO_RETALKER_PATH, "checkpoints")
OUTPUT_PATH = os.path.join(VIDEO_RETALKER_PATH, "output")

# Ensure output directory exists
os.makedirs(OUTPUT_PATH, exist_ok=True)

def process_video(audio_file, face_file):
    """
    Runs Video-Retalker using the uploaded audio and face image.
    """
    if not audio_file or not face_file:
        return "Error: Please upload both an audio file and a face image.", None

    output_video = os.path.join(OUTPUT_PATH, "output.mp4")

    # Command to run Video-Retalker (adjust as needed)
    command = [
        "python", os.path.join(VIDEO_RETALKER_PATH, "inference.py"),
        "--face", face_file,
        "--audio", audio_file,
        "--output", output_video
    ]

    try:
        subprocess.run(command, check=True)
        return "Processing complete! Download your video below:", output_video
    except subprocess.CalledProcessError as e:
        return f"Error: {e}", None

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# 🎭 Video-Retalker Web UI")
    gr.Markdown("Upload an **audio file** and a **face image** to generate a talking face video.")

    with gr.Row():
        audio_input = gr.File(label="Upload Audio (.wav, .mp3)")
        face_input = gr.File(label="Upload Face Image (.jpg, .png)")

    process_button = gr.Button("Generate Talking Video")
    output_text = gr.Textbox(label="Status")
    output_video = gr.File(label="Download Processed Video", interactive=True)

    process_button.click(
        process_video,
        inputs=[audio_input, face_input],
        outputs=[output_text, output_video]
    )

# Launch the Web UI
demo.launch(share=True)
