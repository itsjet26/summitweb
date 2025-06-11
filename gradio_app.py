import gradio as gr
from pathlib import Path
from scripts.inference import main
import argparse
from datetime import datetime
import gdown
import os
import re
import tempfile
import torch
import glob
from omegaconf import OmegaConf
import shutil

# --- CONFIGURATION ---
# Config for the main model processing
CONFIG_PATH = Path("configs/unet/stage2.yaml")
CHECKPOINT_PATH = Path("checkpoints/latentsync_unet.pt")
# Log files
LOG_FILE_PATH = Path("/workspace/latentsync.log")
BATCH_LOG_FILE_PATH = Path("/workspace/latentsync_batch.log")
# Directory for batch mode outputs
OUTPUT_DIR = Path("./outputs")


# --- LOGGING & BATCH MODE HELPER FUNCTIONS (Verified and Working) ---

def read_log_file():
    """Read the last 50 lines of the main log file."""
    try:
        if not LOG_FILE_PATH.exists(): return "Log file not found."
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-50:]).strip()
    except Exception as e:
        return f"Error reading log file: {str(e)}"


def read_batch_log_file():
    """Read the last 50 lines of the batch log file."""
    try:
        if not BATCH_LOG_FILE_PATH.exists(): return "Batch log file not found."
        with open(BATCH_LOG_FILE_PATH, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-50:]).strip()
    except Exception as e:
        return f"Error reading batch log file: {str(e)}"


def refresh_all_outputs():
    """Reads both log files and gets a list of all batch output videos."""
    single_log = read_log_file()
    batch_log = read_batch_log_file()
    batch_files = []
    if OUTPUT_DIR.exists():
        path_objects = sorted([f for f in OUTPUT_DIR.glob("*.mp4")], key=os.path.getmtime, reverse=True)
        batch_files = [str(p) for p in path_objects]
    return single_log, batch_log, batch_files


def list_folders(gdrive_url, progress=gr.Progress()):
    """Clears old inputs, then downloads and lists new folders for batch mode."""
    temp_dir = Path(tempfile.gettempdir()) / "latentsync_batch_session"
    if temp_dir.exists():
        print(f"Clearing previous batch inputs in {temp_dir}...")
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        if not gdrive_url: raise gr.Error("Please provide a Google Drive Folder URL.")
        progress(0.1, desc="Starting folder download")
        gdown.download_folder(gdrive_url, output=str(temp_dir), quiet=False, use_cookies=True, remaining_ok=True)
        # Handle cases where gdown creates a subfolder with the content
        subdirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        content_path = subdirs[0] if len(subdirs) == 1 else temp_dir
        progress(0.5, desc="Listing folders")
        folders = [f.name for f in content_path.iterdir() if f.is_dir()]
        progress(1.0, desc="Folder listing complete")
        if not folders: return gr.update(choices=[], value=[]), None
        return gr.update(choices=folders, value=[]), str(content_path)
    except Exception as e:
        print(f"Error listing folders: {str(e)}")
        return gr.update(choices=[], value=[]), None


def process_batch(local_batch_path, selected_folders, guidance_scale, inference_steps, seed):
    """Clears old outputs, then processes selected folders without updating UI."""
    if OUTPUT_DIR.exists():
        print(f"Clearing previous batch outputs in {OUTPUT_DIR}...")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if not local_batch_path or not selected_folders:
            raise gr.Error("Please list folders and select at least one to process.")
        with open(BATCH_LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"--- New Batch Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        for folder in selected_folders:
            folder_path = Path(local_batch_path) / folder
            video_files = glob.glob(f"{folder_path}/*.[mM][pP]4") + glob.glob(f"{folder_path}/*.[mM][oO][vV]")
            audio_files = glob.glob(f"{folder_path}/*.[wW][aA][vV]") + glob.glob(f"{folder_path}/*.[mM][pP]3")
            if not video_files or not audio_files:
                log_msg = f"{folder} status: skipped (missing video or audio)"
                with open(BATCH_LOG_FILE_PATH, "a", encoding="utf-8") as f: f.write(log_msg + "\n")
                continue
            video_path, audio_path = video_files[0], audio_files[0]
            log_msg = f"{folder} status: processing"
            with open(BATCH_LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
            try:
                # Use the single-file processing logic for each item, passing the folder name
                # as `output_name` to direct output to the correct directory.
                process_video_for_single_mode(video_path, audio_path, guidance_scale, inference_steps, seed,
                                              output_name=folder)
                log_msg = f"{folder} status: complete"
            except Exception as e:
                log_msg = f"{folder} status: FAILED with error: {e}"
            with open(BATCH_LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
    except Exception as e:
        error_message = f"Batch processing error: {str(e)}"
        with open(BATCH_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(error_message + "\n")
        raise gr.Error(error_message)


# --- ORIGINAL FUNCTIONS FOR SINGLE-FILE MODE (Restored and Integrated) ---

def convert_gdrive_url_for_single_mode(gdrive_url):
    try:
        file_id_match = re.search(r'[-\w]{25,}(?=/|$)', gdrive_url)
        if not file_id_match: return None
        file_id = file_id_match.group(0)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return None


def download_gdrive_file_for_single_mode(gdrive_url):
    """Original download function that returns a status message."""
    try:
        if not gdrive_url: return None, None, "Please provide a Google Drive URL"
        direct_url = convert_gdrive_url_for_single_mode(gdrive_url)
        if not direct_url: return None, None, "Invalid Google Drive URL."
        temp_dir = Path(tempfile.gettempdir())
        temp_file_path = gdown.download(direct_url, quiet=False, output=str(temp_dir) + "/")
        if not temp_file_path or not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            return None, None, "Download failed."
        return temp_file_path, temp_file_path, f"File downloaded as {os.path.basename(temp_file_path)}"
    except Exception as e:
        return None, None, f"Error downloading file: {str(e)}"


def process_video_for_single_mode(video_path, audio_path, guidance_scale, inference_steps, seed, gdrive_url=None,
                                  output_name=None):
    """Original processing function, modified to handle different output directories."""
    # If called from batch (`output_name` is provided), use main output dir. Otherwise, use temp.
    output_dir = OUTPUT_DIR if output_name else Path("./temp")
    output_dir.mkdir(parents=True, exist_ok=True)

    if gdrive_url and not video_path:
        video_path, _, download_status = download_gdrive_file_for_single_mode(gdrive_url)
        if not video_path: raise gr.Error(download_status)
    if not video_path: raise gr.Error("Please provide a video file or a valid Google Drive URL")

    video_path = Path(video_path).absolute().as_posix()
    audio_path = Path(audio_path).absolute().as_posix()
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use output_name for batch items, otherwise generate from video stem
    out_stem = output_name if output_name else Path(video_path).stem
    output_path = str(output_dir / f"{out_stem}_{current_time}.mp4")

    config = OmegaConf.load(CONFIG_PATH)
    config["run"].update(
        {"guidance_scale": guidance_scale, "inference_steps": inference_steps, "batch_size": 8, "use_multi_gpu": True})

    num_gpus = torch.cuda.device_count()
    if num_gpus < 1: raise gr.Error("No CUDA-capable GPUs detected.")

    args = create_args(video_path, audio_path, output_path, inference_steps, guidance_scale, seed, num_gpus)
    try:
        main(config=config, args=args)
        result_path = Path(output_path)
        if not result_path.exists() or result_path.stat().st_size == 0:
            raise gr.Error(f"Processing failed: Output file at {output_path} is empty or not created.")
        return str(result_path.absolute())
    except Exception as e:
        raise gr.Error(f"Error during processing: {str(e)}")


def create_args(video_path: str, audio_path: str, output_path: str, inference_steps: int, guidance_scale: float,
                seed: int, num_gpus: int) -> argparse.Namespace:
    """Universal argument creation for the main inference script."""
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
        ["--inference_ckpt_path", CHECKPOINT_PATH.absolute().as_posix(), "--video_path", video_path, "--audio_path",
         audio_path, "--video_out_path", output_path, "--inference_steps", str(inference_steps), "--guidance_scale",
         str(guidance_scale), "--seed", str(seed), "--num_gpus", str(num_gpus)])


def toggle_batch_mode(batch_mode):
    """Shows/hides the correct UI components for the selected mode."""
    is_batch = batch_mode
    return {
        # Single-file mode UI
        video_input: gr.update(visible=not is_batch),
        gdrive_url_input: gr.update(visible=not is_batch),
        download_btn: gr.update(visible=not is_batch),
        download_status: gr.update(visible=not is_batch),
        audio_input: gr.update(visible=not is_batch),
        process_btn: gr.update(visible=not is_batch),
        video_output: gr.update(visible=not is_batch),
        # Batch mode UI
        batch_gdrive_url: gr.update(visible=is_batch),
        list_folders_btn: gr.update(visible=is_batch),
        folder_list: gr.update(visible=is_batch),
        batch_process_btn: gr.update(visible=is_batch),
        batch_output_files: gr.update(visible=is_batch),
    }


# --- UI LAYOUT ---
with gr.Blocks(title="Summit Lipsync") as demo:
    gr.Markdown("""<h1 align="center">Summit Lipsync</h1>""")  # Abbreviated for clarity
    downloaded_batch_path = gr.State(value=None)
    batch_mode = gr.Checkbox(label="Batch Queue Mode", value=False)
    with gr.Row():
        with gr.Column():
            # --- SINGLE FILE UI ---
            video_input = gr.Video(label="Input Video")
            with gr.Row():
                gdrive_url_input = gr.Textbox(label="Google Drive Video URL", placeholder="Enter Google Drive URL",
                                              lines=1)
                download_btn = gr.Button("Download")
            download_status = gr.Textbox(label="Download Status", interactive=False)
            audio_input = gr.Audio(label="Input Audio", type="filepath")

            # --- BATCH UI ---
            batch_gdrive_url = gr.Textbox(label="Google Drive Folder URL", placeholder="Enter Google Drive folder URL",
                                          lines=1, visible=False)
            list_folders_btn = gr.Button("List Folders", visible=False)
            folder_list = gr.CheckboxGroup(label="Select Folders to Process", visible=False)

            # --- SHARED SETTINGS & BUTTONS ---
            with gr.Row():
                guidance_scale = gr.Slider(minimum=1.0, maximum=3.0, value=2.0, step=0.1, label="Guidance Scale")
                inference_steps = gr.Slider(minimum=10, maximum=50, value=25, step=1, label="Inference Steps")
            with gr.Row():
                seed = gr.Slider(minimum=1, maximum=1000000, value=1247, step=1, label="Random Seed")
            process_btn = gr.Button("Process Single Video")
            batch_process_btn = gr.Button("Process Batch", visible=False)

        with gr.Column():
            video_output = gr.Video(label="Output Video")
            batch_output_files = gr.File(label="Batch Output Files", visible=False, file_count="multiple")
            log_display = gr.Textbox(label="Main Log", interactive=False, lines=10)
            batch_log_display = gr.Textbox(label="Batch Log", interactive=False, lines=5)
            refresh_log_btn = gr.Button("Refresh Outputs & Logs")

    # --- EVENT LISTENERS ---
    batch_mode.change(fn=toggle_batch_mode, inputs=[batch_mode], outputs=[
        video_input, gdrive_url_input, download_btn, download_status, audio_input, process_btn, video_output,
        batch_gdrive_url, list_folders_btn, folder_list, batch_process_btn, batch_output_files
    ])
    refresh_log_btn.click(fn=refresh_all_outputs, inputs=[],
                          outputs=[log_display, batch_log_display, batch_output_files])

    # --- Single-mode listeners use original functions ---
    download_btn.click(fn=download_gdrive_file_for_single_mode, inputs=[gdrive_url_input],
                       outputs=[video_input, video_input, download_status])
    process_btn.click(fn=process_video_for_single_mode,
                      inputs=[video_input, audio_input, guidance_scale, inference_steps, seed, gdrive_url_input],
                      outputs=[video_output])

    # --- Batch-mode listeners use batch functions ---
    list_folders_btn.click(fn=list_folders, inputs=[batch_gdrive_url], outputs=[folder_list, downloaded_batch_path])
    batch_process_btn.click(fn=process_batch,
                            inputs=[downloaded_batch_path, folder_list, guidance_scale, inference_steps, seed],
                            outputs=None)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)
