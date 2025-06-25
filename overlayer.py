import gradio as gr
import cv2
import numpy as np
import os
import tempfile
import random
import gdown
from pathlib import Path
import re
import shutil
import traceback
import zipfile
import subprocess


# --- GPU Detection & Core Video Processing Functions ---

def is_nvidia_gpu_available():
    """
    Checks if nvidia-smi command is available, which is a reliable indicator
    that an NVIDIA GPU and drivers are present.
    """
    return shutil.which('nvidia-smi') is not None


def remove_green_background_with_alpha(frame):
    """
    Removes green screen from a BGR frame and returns an RGBA image.
    This is used only for generating the static PNG previews.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    alpha_channel = cv2.bitwise_not(mask)
    b, g, r = cv2.split(frame)
    # Merge B, G, R, and the new Alpha channel
    bgra = cv2.merge([b, g, r, alpha_channel])
    # Convert from BGRA to RGBA for proper display in RGB-based libraries
    return cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA)


def overlay_alpha(background_rgb, foreground_rgba, x, y):
    """
    Overlays an RGBA (foreground) image onto an RGB (background) image.
    This is used only for generating the static PNG previews.
    """
    fg_h, fg_w, _ = foreground_rgba.shape
    bg_h, bg_w, _ = background_rgb.shape

    alpha = foreground_rgba[:, :, 3] / 255.0
    alpha_3 = np.stack([alpha] * 3, axis=-1)
    foreground_rgb = foreground_rgba[:, :, :3]

    y1, x1 = max(0, y), max(0, x)
    y2, x2 = min(bg_h, y + fg_h), min(bg_w, x + fg_w)

    fg_y1, fg_x1 = max(0, -y), max(0, -x)
    fg_y2, fg_x2 = fg_y1 + (y2 - y1), fg_x1 + (x2 - x1)

    if y2 <= y1 or x2 <= x1:
        return background_rgb

    bg_roi = background_rgb[y1:y2, x1:x2]
    fg_crop = foreground_rgb[fg_y1:fg_y2, fg_x1:fg_x2]
    alpha_crop = alpha_3[fg_y1:fg_y2, fg_x1:fg_x2]

    composite_roi = (fg_crop * alpha_crop) + (bg_roi * (1 - alpha_crop))
    background_rgb[y1:y2, x1:x2] = composite_roi.astype(np.uint8)
    return background_rgb


# --- File Download Functions (Unchanged) ---

def convert_gdrive_url_for_single_mode(gdrive_url):
    try:
        file_id_match = re.search(r'[-\w]{25,}(?=/|$)', gdrive_url)
        if not file_id_match: return None
        file_id = file_id_match.group(0)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return None


def download_gdrive_file_for_single_mode(gdrive_url):
    try:
        if not gdrive_url: return None, gr.update(value="Please provide a Google Drive URL", visible=True)
        direct_url = convert_gdrive_url_for_single_mode(gdrive_url)
        if not direct_url: return None, gr.update(value="Invalid Google Drive URL.", visible=True)
        script_dir = Path(__file__).parent
        download_dir = script_dir / "downloaded_files"
        download_dir.mkdir(parents=True, exist_ok=True)
        temp_basename = f"gdown_single_temp_{os.urandom(4).hex()}"
        target_path_for_gdown = download_dir / temp_basename
        final_downloaded_path = gdown.download(direct_url, quiet=False, output=str(target_path_for_gdown))
        temp_file_path = Path(final_downloaded_path)
        if not temp_file_path.exists() or temp_file_path.stat().st_size == 0: return None, gr.update(
            value="Download failed", visible=True)
        new_file_path = temp_file_path.with_suffix('.mp4')
        if temp_file_path != new_file_path: os.rename(temp_file_path, new_file_path)
        return str(new_file_path), gr.update(value=f"File downloaded as {new_file_path.name}", visible=True)
    except Exception as e:
        return None, gr.update(value=f"Error: {str(e)}", visible=True)


def download_gdrive_folder(gdrive_url, progress=gr.Progress()):
    try:
        if not gdrive_url: return None, gr.update(value="Please provide a Google Drive Folder URL.", visible=True)
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as temp_dir:
            temp_dir_path = Path(temp_dir)
            progress(0.1, desc="Starting folder download")
            output_dir = str(temp_dir_path / "avatar_folder")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            gdown.download_folder(gdrive_url, output=output_dir, quiet=False, use_cookies=True, remaining_ok=True)
            downloaded_folder_path = Path(output_dir)
            if not downloaded_folder_path.exists() or not downloaded_folder_path.is_dir(): return None, gr.update(
                value="Folder download failed", visible=True)
            progress(0.5, desc="Processing downloaded videos")
            video_files_list = []
            for file_path in downloaded_folder_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in (
                '.mp4', '.avi', '.mov', '.webm', '.flv', '.wmv'):
                    new_file_path = file_path.with_suffix('.mp4')
                    if file_path != new_file_path:
                        try:
                            os.rename(file_path, new_file_path)
                        except Exception as e:
                            continue
                    video_files_list.append(new_file_path)
            if not video_files_list: return None, gr.update(value="No valid video files found.", visible=True)
            script_dir = Path(__file__).parent
            persistent_dir = script_dir / "downloaded_avatar_folders"
            if persistent_dir.exists(): shutil.rmtree(persistent_dir)
            persistent_dir.mkdir(parents=True, exist_ok=True)
            persistent_file_paths = []
            for file_path in video_files_list:
                dest_path = persistent_dir / file_path.name
                shutil.copy(file_path, dest_path)
                persistent_file_paths.append(str(dest_path))
            progress(1.0, desc="Folder download complete")
            return persistent_file_paths, gr.update(value=f"Downloaded {len(persistent_file_paths)} files.",
                                                    visible=True)
    except Exception as e:
        print(traceback.format_exc())
        return None, gr.update(value=f"Error: {str(e)}", visible=True)


# --- Preview Generation Function (Unchanged) ---
def generate_all_previews(main_video_path, avatar_file_paths, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Upload both a main video and avatar videos for previews.")
        return [], []
    video_params_list = []
    preview_paths = []
    main_cap_temp = cv2.VideoCapture(str(main_video_path))
    if not main_cap_temp.isOpened():
        gr.Warning(f"Could not open main video: {main_video_path}")
        return [], []
    ret_main, initial_main_frame_bgr = main_cap_temp.read()
    main_cap_temp.release()
    if not ret_main:
        gr.Warning("Could not read first frame from main video.")
        return [], []
    main_h, main_w, _ = initial_main_frame_bgr.shape
    script_dir = Path(__file__).parent
    preview_output_dir = script_dir / "generated_previews"
    preview_output_dir.mkdir(parents=True, exist_ok=True)
    for avatar_video_path_str in progress.tqdm(avatar_file_paths, desc="Generating Previews"):
        try:
            avatar_video_path = Path(avatar_video_path_str)
            avatar_cap = cv2.VideoCapture(str(avatar_video_path))
            if not avatar_cap.isOpened(): continue
            ret_avatar, avatar_frame_bgr = avatar_cap.read()
            avatar_cap.release()
            if not ret_avatar: continue
            params = {}
            params['zoom_factor'] = random.uniform(1.0, 1.2)
            cropped_width = int(main_w / params['zoom_factor'])
            cropped_height = int(main_h / params['zoom_factor'])
            params['crop_x'] = random.randint(0, main_w - cropped_width)
            params['crop_y'] = random.randint(0, main_h - cropped_height)
            target_avatar_height = random.uniform(main_h / 4, main_h / 3)
            avatar_aspect_ratio = avatar_frame_bgr.shape[1] / avatar_frame_bgr.shape[0]
            params['scaled_avatar_h'] = int(target_avatar_height)
            params['scaled_avatar_w'] = int(params['scaled_avatar_h'] * avatar_aspect_ratio)
            right_boundary = (main_w // 2) - params['scaled_avatar_w']
            params['x_pos'] = random.randint(0, max(0, right_boundary))
            params['y_pos'] = main_h - params['scaled_avatar_h']
            video_params_list.append(params)
            processed_main_frame = initial_main_frame_bgr[params['crop_y']:params['crop_y'] + cropped_height,
                                   params['crop_x']:params['crop_x'] + cropped_width]
            processed_main_frame = cv2.resize(processed_main_frame, (main_w, main_h), interpolation=cv2.INTER_AREA)
            resized_avatar_frame = cv2.resize(avatar_frame_bgr, (params['scaled_avatar_w'], params['scaled_avatar_h']),
                                              interpolation=cv2.INTER_AREA)
            avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)
            processed_main_rgb = cv2.cvtColor(processed_main_frame, cv2.COLOR_BGR2RGB)
            composite_frame_rgb = overlay_alpha(processed_main_rgb.copy(), avatar_rgba, params['x_pos'],
                                                params['y_pos'])
            preview_filename = f"preview_{avatar_video_path.stem}.png"
            preview_path = preview_output_dir / preview_filename
            cv2.imwrite(str(preview_path), cv2.cvtColor(composite_frame_rgb, cv2.COLOR_RGB2BGR))
            preview_paths.append(str(preview_path))
        except Exception as e:
            print(traceback.format_exc())
            continue
    return video_params_list, preview_paths


# --- Video Generation Function with Best Quality Presets ---
def generate_videos_and_zip(main_video_path, avatar_file_paths, video_params, parallel_mode, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Upload both a main video and avatar videos.")
        return [], None, gr.update(visible=False)
    if not video_params:
        gr.Warning("Please generate previews first to set the video layouts.")
        return [], None, gr.update(visible=False)

    generated_video_paths = []
    script_dir = Path(__file__).parent
    video_output_dir = script_dir / "generated_videos"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    main_clip_info = cv2.VideoCapture(str(main_video_path))
    main_width = int(main_clip_info.get(cv2.CAP_PROP_FRAME_WIDTH))
    main_height = int(main_clip_info.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = main_clip_info.get(cv2.CAP_PROP_FPS)
    main_clip_info.release()
    if fps == 0:
        fps = 30

    # Dynamically select encoder and BEST QUALITY settings based on GPU availability
    if is_nvidia_gpu_available():
        # Best quality settings for NVIDIA's NVENC encoder
        encoding_settings = [
            '-c:v', 'h264_nvenc',
            '-preset', 'p7',  # p7 is the slowest/best quality preset for NVENC
            '-rc', 'vbr',  # Use Variable Bitrate for rate control
            '-cq', '19',  # Constant Quality level, lower is better (19 is excellent)
            '-b:v', '0',  # Required for constant quality mode
        ]
    else:
        # Best quality settings for the libx264 (CPU) encoder
        encoding_settings = [
            '-c:v', 'libx264',
            '-preset', 'slow',  # 'slow' offers a great quality/time balance for archiving
            '-crf', '18',  # Lower CRF is higher quality (18 is considered visually lossless)
        ]

    for i, avatar_path_str in enumerate(progress.tqdm(avatar_file_paths, desc="Generating Videos")):
        try:
            params = video_params[i]
            avatar_path = Path(avatar_path_str)
            output_filename = f"final_{'parallel' if parallel_mode else 'sequential'}_{avatar_path.stem}.mp4"
            output_path = video_output_dir / output_filename

            crop_x, crop_y = params['crop_x'], params['crop_y']
            zoom_factor = params['zoom_factor']
            cropped_width = int(main_width / zoom_factor)
            cropped_height = int(main_height / zoom_factor)
            scaled_avatar_w, scaled_avatar_h = params['scaled_avatar_w'], params['scaled_avatar_h']
            x_pos, y_pos = params['x_pos'], params['y_pos']

            ffmpeg_command = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-i', str(main_video_path),
                '-i', str(avatar_path),
            ]

            colorkey_setting = "colorkey=0x00FF00:0.4:0.1"

            if parallel_mode:
                filter_complex = (
                    f"[0:v]crop={cropped_width}:{cropped_height}:{crop_x}:{crop_y},scale={main_width}:{main_height},setsar=1[main_processed];"
                    f"[1:v]format=yuv444p,{colorkey_setting},scale={scaled_avatar_w}:{scaled_avatar_h},setsar=1[avatar_processed];"
                    f"[main_processed][avatar_processed]overlay={x_pos}:{y_pos}[final_v];"
                    f"[0:a][1:a]amix=inputs=2:duration=first[final_a]"
                )
                ffmpeg_command.extend(['-filter_complex', filter_complex, '-map', '[final_v]', '-map', '[final_a]'])
            else:
                # Refactored filter graph for sequential mode for more robustness
                filter_complex = (
                    # Split the main video into two identical streams
                    f"[0:v]split[main_for_bg][main_for_concat];"
                    # Create the frozen background from the first stream
                    f"[main_for_bg]trim=end_frame=1,loop=-1:size=1,setpts=PTS-STARTPTS,fps={fps},crop={cropped_width}:{cropped_height}:{crop_x}:{crop_y},scale={main_width}:{main_height},setsar=1[frozen_bg];"
                    # Process the avatar video
                    f"[1:v]format=yuv444p,{colorkey_setting},scale={scaled_avatar_w}:{scaled_avatar_h},setsar=1[avatar_processed];"
                    # Overlay avatar on the frozen background
                    f"[frozen_bg][avatar_processed]overlay={x_pos}:{y_pos}:shortest=1[part1_v];"
                    # Process the second main video stream for concatenation
                    f"[main_for_concat]crop={cropped_width}:{cropped_height}:{crop_x}:{crop_y},scale={main_width}:{main_height},setsar=1[part2_v];"
                    # Concatenate the video and audio streams
                    f"[part1_v][1:a][part2_v][0:a]concat=n=2:v=1:a=1[final_v][final_a]"
                )
                ffmpeg_command.extend(['-filter_complex', filter_complex, '-map', '[final_v]', '-map', '[final_a]'])

            # Apply the selected high-quality encoding settings
            ffmpeg_command.extend(encoding_settings)
            # Apply audio settings and output path
            ffmpeg_command.extend(['-c:a', 'aac', '-b:a', '192k', '-y', str(output_path)])

            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
            generated_video_paths.append(str(output_path))

        except subprocess.CalledProcessError as e:
            # Fixed the TypeError here by converting all args to strings before joining
            print("--- FFMPEG COMMAND FAILED ---")
            print("Command:", ' '.join(map(str, e.args)))
            print("Return Code:", e.returncode)
            print("--- FFMPEG STDERR ---")
            print(e.stderr if e.stderr else "N/A")
            print("-----------------------------")
            continue
        except Exception as e:
            print(f"An unexpected error occurred while processing {avatar_path_str}:")
            print(traceback.format_exc())
            continue

    # After generating all videos, create the zip file if any videos were created
    if not generated_video_paths:
        return [], None, gr.update(visible=False)

    progress(0.9, desc="Zipping files...")
    # Create the zip in the same directory as the generated videos
    zip_filename = f"generated_videos_{os.urandom(4).hex()}.zip"
    zip_path = video_output_dir / zip_filename

    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file_path_str in generated_video_paths:
            file_path = Path(file_path_str)
            zf.write(file_path, arcname=file_path.name)

    # Return paths for the file list, the path for the zip file, and make the button visible
    return generated_video_paths, str(zip_path), gr.update(visible=True)


def get_zip_path(zip_path_from_state):
    """
    A simple function to retrieve the zip path from the state and provide it to the download button.
    This makes the download action feel instantaneous to the user.
    """
    return zip_path_from_state


# --- Gradio UI Setup ---
with gr.Blocks(title="Advanced Avatar Overlay App", theme=gr.themes.Soft()) as demo:
    gpu_detected = is_nvidia_gpu_available()
    gpu_status = "✅ NVIDIA GPU Detected: Using `h264_nvenc` for hardware acceleration." if gpu_detected else "⚠️ No NVIDIA GPU Detected: Falling back to CPU-based `libx264` encoder."

    gr.Markdown("# Advanced Avatar Overlay App (FFMPEG Powered)")
    gr.Markdown(gpu_status)
    gr.Markdown("---")
    gr.Markdown("Create dynamic videos by overlaying a green-screen avatar onto a main video.")

    video_params_state = gr.State([])
    # State to hold the path of the final zip file
    zip_path_state = gr.State(None)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload Main Video")
            main_video_input = gr.Video(label="Upload Main Video")
            gdrive_url_main = gr.Textbox(label="Or, Google Drive URL for Main Video",
                                         placeholder="Enter Google Drive File URL", lines=1)
            gdrive_main_btn = gr.Button("Download Main Video from URL")
            main_video_status = gr.Textbox(label="Download Status", interactive=False, visible=False)
        with gr.Column(scale=1):
            gr.Markdown("### 2. Upload Avatar Videos")
            avatar_file_input = gr.File(label="Upload Green Screen Avatar Videos", file_count="multiple",
                                        file_types=["video"], type="filepath")
            gdrive_url_avatar = gr.Textbox(label="Or, Google Drive URL for Avatars",
                                           placeholder="Enter Google Drive Folder URL", lines=1)
            gdrive_avatar_btn = gr.Button("Download Avatars from Folder URL")
            avatar_folder_status = gr.Textbox(label="Download Status", interactive=False, visible=False)
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### 3. Generate Previews & Videos")
            preview_btn = gr.Button("A) Generate Randomized Previews", variant="secondary")
            gr.Markdown("First, generate previews to lock-in a random layout for each video.")
            parallel_mode_checkbox = gr.Checkbox(label="Parallel Mode (Avatar and main video play at the same time)",
                                                 value=True)
            generate_btn = gr.Button("B) Generate Final Videos & ZIP", variant="primary")
            gr.Markdown("Second, generate the final high-quality videos and prepare the ZIP file for download.")

    with gr.Tabs():
        with gr.TabItem("Previews"):
            generated_previews_gallery = gr.Gallery(label="Generated Previews", columns=6, object_fit="contain",
                                                    height="auto")
        with gr.TabItem("Final Videos"):
            generated_videos_output = gr.File(label="Generated Videos (Click to Download)", file_count="multiple",
                                              interactive=False)
            # The Download All button is now re-instated
            download_all_btn = gr.DownloadButton("Download All as ZIP", variant="primary", visible=False)

    preview_btn.click(fn=generate_all_previews, inputs=[main_video_input, avatar_file_input],
                      outputs=[video_params_state, generated_previews_gallery])

    generate_btn.click(
        fn=generate_videos_and_zip,
        inputs=[main_video_input, avatar_file_input, video_params_state, parallel_mode_checkbox],
        outputs=[generated_videos_output, zip_path_state, download_all_btn]
    )

    # This click event now triggers the instant download of the pre-made zip file
    download_all_btn.click(
        fn=get_zip_path,
        inputs=[zip_path_state],
        outputs=download_all_btn
    )

    gdrive_main_btn.click(fn=download_gdrive_file_for_single_mode, inputs=[gdrive_url_main],
                          outputs=[main_video_input, main_video_status])
    gdrive_avatar_btn.click(fn=download_gdrive_folder, inputs=[gdrive_url_avatar],
                            outputs=[avatar_file_input, avatar_folder_status])

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    for folder in ["generated_videos", "generated_previews", "downloaded_avatar_folders", "downloaded_files"]:
        dir_to_clean = script_dir / folder
        if dir_to_clean.exists():
            print(f"Cleaning up old directory: {dir_to_clean}")
            shutil.rmtree(dir_to_clean)
    demo.launch(server_name="0.0.0.0", server_port=7864)
