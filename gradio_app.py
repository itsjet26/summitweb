import gradio as gr
from pathlib import Path
from scripts.inference import main
from omegaconf import OmegaConf
import argparse
from datetime import datetime
import gdown
import os
import re
import tempfile
import torch

CONFIG_PATH = Path("configs/unet/stage2.yaml")
CHECKPOINT_PATH = Path("checkpoints/latentsync_unet.pt")
LOG_FILE_PATH = Path("/workspace/latentsync.log")


def read_log_file():
    """Read the last 50 lines of the log file."""
    try:
        if not LOG_FILE_PATH.exists():
            return "Log file not found at /workspace/latentsync.log"
        with open(LOG_FILE_PATH, "r") as f:
            lines = f.readlines()
            return "".join(lines[-50:]).strip()
    except Exception as e:
        return f"Error reading log file: {str(e)}"


def convert_gdrive_url(gdrive_url):
    try:
        file_id_match = re.search(r'[-\w]{25,}(?=/|$)', gdrive_url)
        if not file_id_match:
            return None
        file_id = file_id_match.group(0)
        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return direct_url
    except:
        return None


def download_gdrive_file(gdrive_url):
    try:
        if not gdrive_url:
            return None, None, "Please provide a Google Drive URL"
        direct_url = convert_gdrive_url(gdrive_url)
        if not direct_url:
            return None, None, "Invalid Google Drive URL. Ensure it contains a valid file ID (e.g., https://drive.google.com/file/d/FILE_ID/view)."
        temp_dir = Path(tempfile.gettempdir())
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = gdown.download(direct_url, quiet=False, output=str(temp_dir) + "/")
        if not temp_file_path or not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            return None, None, "Download failed. The file may be empty or inaccessible."
        print(
            f"Downloaded file: {temp_file_path}, exists: {os.path.exists(temp_file_path)}, size: {os.path.getsize(temp_file_path)} bytes")
        return temp_file_path, temp_file_path, f"File downloaded successfully as {os.path.basename(temp_file_path)}"
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return None, None, f"Error downloading file: {str(e)}"


def process_video(
        video_path,
        audio_path,
        guidance_scale,
        inference_steps,
        seed,
        gdrive_url=None
):
    output_dir = Path("./temp")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle Google Drive URL if provided and no video_path
    if gdrive_url and not video_path:
        video_path, _, download_status = download_gdrive_file(gdrive_url)
        if not video_path:
            raise gr.Error(download_status)

    if not video_path:
        raise gr.Error("Please provide a video file or a valid Google Drive URL")
    video_file_path = Path(video_path)
    print(f"Input video path: {video_file_path}, exists: {video_file_path.exists()}")
    if not video_file_path.exists():
        raise gr.Error(f"Video file not found at {video_file_path}")
    video_path = video_file_path.absolute().as_posix()
    audio_path = Path(audio_path).absolute().as_posix()
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(output_dir / f"{Path(video_path).stem}_{current_time}.mp4")
    print(f"Output video path: {output_path}")
    config = OmegaConf.load(CONFIG_PATH)
    config["run"].update(
        {
            "guidance_scale": guidance_scale,
            "inference_steps": inference_steps,
            "batch_size": 8,
            "use_multi_gpu": True,
        }
    )
    num_gpus = torch.cuda.device_count()
    print(f"Detected {num_gpus} GPUs: {[torch.cuda.get_device_name(i) for i in range(num_gpus)]}")
    if num_gpus < 1:
        raise gr.Error("No CUDA-capable GPUs detected. Ensure CUDA is installed and GPUs are available.")
    elif num_gpus == 1:
        print("Only one GPU detected; multi-GPU optimization will not apply.")
    args = create_args(video_path, audio_path, output_path, inference_steps, guidance_scale, seed, num_gpus)
    try:
        print(f"Calling main with video_path={video_path}, audio_path={audio_path}, output_path={output_path}")
        if num_gpus > 1:
            print("Enabling multi-GPU processing with DataParallel")
        result = main(
            config=config,
            args=args,
        )
        print(f"Main returned: {result}")
        result_path = Path(output_path)
        if not result_path.exists():
            print(f"Error: Output file does not exist at {output_path}")
            raise gr.Error(f"Processing failed: Output file not found at {output_path}")
        if result_path.stat().st_size == 0:
            print(f"Error: Output file at {output_path} is empty")
            raise gr.Error(f"Processing failed: Output file at {output_path} is empty")
        print(
            f"Processing completed successfully. Output file: {output_path}, size: {result_path.stat().st_size} bytes")
        return str(result_path.absolute())
    except Exception as e:
        error_msg = str(e)
        print(f"Error during processing: {error_msg}")
        if "stack expects a non-empty TensorList" in error_msg:
            error_msg = "No faces detected in the video. Please use a video with at least one visible face."
        elif "Could not open video" in error_msg:
            error_msg = f"Could not open video at {video_path}. Ensure the file is a valid video format (e.g., .mp4)."
        elif "Processing failed" not in error_msg:
            error_msg = f"Unexpected error: {error_msg}"
        print(f"Final error message: {error_msg}")
        raise gr.Error(f"Error during processing: {error_msg}")


def create_args(
        video_path: str, audio_path: str, output_path: str, inference_steps: int, guidance_scale: float, seed: int,
        num_gpus: int
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inference_ckpt_path", type=str, required=True)
    parser.add_argument("--video_path", type=str, required=True)
    parser.add_argument("--audio_path", type=str, required=True)
    parser.add_argument("--video_out_path", type=str, required=True)
    parser.add_argument("--inference_steps", type=int, default=20)
    parser.add_argument("--guidance_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1247)
    parser.add_argument("--num_gpus", type=int, default=1)
    return parser.parse_args(
        [
            "--inference_ckpt_path",
            CHECKPOINT_PATH.absolute().as_posix(),
            "--video_path",
            video_path,
            "--audio_path",
            audio_path,
            "--video_out_path",
            output_path,
            "--inference_steps",
            str(inference_steps),
            "--guidance_scale",
            str(guidance_scale),
            "--seed",
            str(seed),
            "--num_gpus",
            str(num_gpus),
        ]
    )


with gr.Blocks(title="LatentSync demo") as demo:
    gr.Markdown(
        """
        <h1 align="center">LatentSync</h1>

        <div style="display:flex;justify-content:center;column-gap:4px;">
            <a href="https://github.com/bytedance/LatentSync">
                <img src='https://img.shields.io/badge/GitHub-Repo-blue'>
            </a> 
            <a href="https://arxiv.org/abs/2412.09262">
                <img src='https://img.shields.io/badge/arXiv-Paper-red'>
            </a>
        </div>
        """
    )
    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="Input Video")
            with gr.Row():
                gdrive_url_input = gr.Textbox(
                    label="Google Drive Video URL",
                    placeholder="Enter Google Drive URL (e.g., https://drive.google.com/file/d/FILE_ID/view)",
                    lines=1
                )
                download_btn = gr.Button("Download")
            download_status = gr.Textbox(label="Download Status", interactive=False)
            audio_input = gr.Audio(label="Input Audio", type="filepath")
            with gr.Row():
                guidance_scale = gr.Slider(
                    minimum=1.0,
                    maximum=3.0,
                    value=2.0,
                    step=0.5,
                    label="Guidance Scale",
                )
                inference_steps = gr.Slider(minimum=10, maximum=50, value=20, step=1, label="Inference Steps")
            with gr.Row():
                seed = gr.Number(value=1247, label="Random Seed", precision=0)
            process_btn = gr.Button("Process Video")
        with gr.Column():
            video_output = gr.Video(label="Output Video")
            gr.Examples(
                examples=[
                    ["assets/demo1_video.mp4", "assets/demo1_audio.wav"],
                    ["assets/demo2_video.mp4", "assets/demo2_audio.wav"],
                    ["assets/demo3_video.mp4", "assets/demo3_audio.wav"],
                ],
                inputs=[video_input, audio_input],
            )
            log_display = gr.Textbox(label="Log File (/workspace/latentsync.log)", interactive=False, lines=10)
            refresh_log_btn = gr.Button("Refresh Log")
    refresh_log_btn.click(
        fn=read_log_file,
        inputs=[],
        outputs=[log_display]
    )
    download_btn.click(
        fn=download_gdrive_file,
        inputs=[gdrive_url_input],
        outputs=[video_input, video_input, download_status]
    )
    process_btn.click(
        fn=process_video,
        inputs=[
            video_input,
            audio_input,
            guidance_scale,
            inference_steps,
            seed,
            gdrive_url_input
        ],
        outputs=[video_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)
