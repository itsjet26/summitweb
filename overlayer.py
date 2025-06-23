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
import subprocess  # <-- FFMPEG is now used via subprocess


# --- Core Video Processing Functions (No changes here) ---

def remove_green_background_with_alpha(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    alpha_channel = cv2.bitwise_not(mask)
    b, g, r = cv2.split(frame)
    # Convert back to RGBA for compositing
    return cv2.cvtColor(cv2.merge([b, g, r, alpha_channel]), cv2.COLOR_BGRA2RGBA)


def overlay_alpha(background_rgb, foreground_rgba, x, y):
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


# --- File Download Functions (No changes here) ---

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


# --- Preview Function (Unchanged) ---
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
    return preview_paths, video_params_list


# --- REFACTORED Video Generation Function (OpenCV for Video + FFMPEG for Audio) ---
def generate_videos(main_video_path, avatar_file_paths, video_params, parallel_mode, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Upload both a main video and avatar videos.")
        return [], gr.update(visible=False)
    if not video_params:
        gr.Warning("Please generate previews first to set the video layouts.")
        return [], gr.update(visible=False)

    generated_video_paths = []
    script_dir = Path(__file__).parent
    video_output_dir = script_dir / "generated_videos"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    main_clip_info = cv2.VideoCapture(str(main_video_path))
    fps = main_clip_info.get(cv2.CAP_PROP_FPS)
    main_width = int(main_clip_info.get(cv2.CAP_PROP_FRAME_WIDTH))
    main_height = int(main_clip_info.get(cv2.CAP_PROP_FRAME_HEIGHT))
    main_clip_info.release()

    for i, avatar_path_str in enumerate(progress.tqdm(avatar_file_paths, desc="Generating Videos")):
        temp_silent_video_path = None
        try:
            # --- 1. Load parameters and create list for visual frames ---
            params = video_params[i]
            x_pos, y_pos = params['x_pos'], params['y_pos']
            crop_x, crop_y = params['crop_x'], params['crop_y']
            zoom_factor = params['zoom_factor']
            cropped_width = int(main_width / zoom_factor)
            cropped_height = int(main_height / zoom_factor)
            scaled_avatar_w, scaled_avatar_h = params['scaled_avatar_w'], params['scaled_avatar_h']

            # --- 2. Generate Visuals with OpenCV ---
            main_cap = cv2.VideoCapture(str(main_video_path))
            avatar_cap = cv2.VideoCapture(str(avatar_path_str))

            # This list will hold the final RGB frames for this specific video
            processed_frames_for_this_video = []

            if parallel_mode:
                while True:
                    ret_main, main_frame_bgr = main_cap.read()
                    ret_avatar, avatar_frame_bgr = avatar_cap.read()
                    if not ret_main: break
                    if not ret_avatar:
                        avatar_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret_avatar, avatar_frame_bgr = avatar_cap.read()
                        if not ret_avatar: break
                    main_processed_bgr = cv2.resize(
                        main_frame_bgr[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width],
                        (main_width, main_height))
                    avatar_resized_bgr = cv2.resize(avatar_frame_bgr, (scaled_avatar_w, scaled_avatar_h))
                    avatar_rgba = remove_green_background_with_alpha(avatar_resized_bgr)
                    main_processed_rgb = cv2.cvtColor(main_processed_bgr, cv2.COLOR_BGR2RGB)
                    composite_frame = overlay_alpha(main_processed_rgb.copy(), avatar_rgba, x_pos, y_pos)
                    processed_frames_for_this_video.append(composite_frame)
            else:  # Sequential Mode
                ret_first, first_main_frame_bgr = main_cap.read()
                if ret_first:
                    frozen_main_bgr = cv2.resize(
                        first_main_frame_bgr[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width],
                        (main_width, main_height))
                    frozen_main_rgb = cv2.cvtColor(frozen_main_bgr, cv2.COLOR_BGR2RGB)
                    while True:
                        ret_avatar, avatar_frame_bgr = avatar_cap.read()
                        if not ret_avatar: break
                        avatar_resized_bgr = cv2.resize(avatar_frame_bgr, (scaled_avatar_w, scaled_avatar_h))
                        avatar_rgba = remove_green_background_with_alpha(avatar_resized_bgr)
                        composite_frame = overlay_alpha(frozen_main_rgb.copy(), avatar_rgba, x_pos, y_pos)
                        processed_frames_for_this_video.append(composite_frame)
                main_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                while True:
                    ret_main, main_frame_bgr = main_cap.read()
                    if not ret_main: break
                    main_processed_bgr = cv2.resize(
                        main_frame_bgr[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width],
                        (main_width, main_height))
                    processed_frames_for_this_video.append(cv2.cvtColor(main_processed_bgr, cv2.COLOR_BGR2RGB))

            main_cap.release()
            avatar_cap.release()

            if not processed_frames_for_this_video:
                continue

            # --- 3. Write silent video using OpenCV ---
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                temp_silent_video_path = tmp.name

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_silent_video_path, fourcc, fps, (main_width, main_height))
            for frame_rgb in processed_frames_for_this_video:
                # cv2.VideoWriter expects BGR frames, so we convert back from RGB
                out.write(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
            out.release()

            # --- 4. Add audio using FFMPEG ---
            output_filename = f"final_{'parallel' if parallel_mode else 'sequential'}_{Path(avatar_path_str).stem}.mp4"
            output_path = video_output_dir / output_filename

            ffmpeg_command = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-i', temp_silent_video_path,  # Input 0: Silent video
                '-i', main_video_path,  # Input 1: Main video (for audio)
                '-i', avatar_path_str,  # Input 2: Avatar video (for audio)
            ]

            if parallel_mode:
                # Mix audio from main (input 1) and avatar (input 2)
                filter_complex = "[1:a][2:a]amix=inputs=2:duration=first[a]"
                ffmpeg_command.extend(['-filter_complex', filter_complex, '-map', '0:v', '-map', '[a]'])
            else:  # Sequential Mode
                # Concatenate audio from avatar (input 2) then main (input 1)
                filter_complex = "[2:a][1:a]concat=n=2:v=0:a=1[a]"
                ffmpeg_command.extend(['-filter_complex', filter_complex, '-map', '0:v', '-map', '[a]'])

            # Use -c:v copy to avoid re-encoding the video stream, which is very fast.
            # -shortest ensures the output terminates with the video stream.
            ffmpeg_command.extend(['-c:v', 'copy', '-c:a', 'aac', '-shortest', '-y', str(output_path)])

            subprocess.run(ffmpeg_command, check=True)
            generated_video_paths.append(str(output_path))

        except Exception as e:
            print(traceback.format_exc())
            continue
        finally:
            # --- 5. Clean up temporary silent file ---
            if temp_silent_video_path and os.path.exists(temp_silent_video_path):
                os.remove(temp_silent_video_path)

    return generated_video_paths, gr.update(visible=True)


# --- "Download All" Function ---
def zip_videos(file_list):
    if not file_list:
        gr.Warning("No videos have been generated to download!")
        return None
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = tmp_zip.name
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file_data in file_list:
            file_path = Path(file_data.path)
            zf.write(file_path, arcname=file_path.name)
    return zip_path


# --- Gradio UI Setup ---
with gr.Blocks(title="Advanced Avatar Overlay App", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Advanced Avatar Overlay App (OpenCV + FFMPEG)")
    gr.Markdown(
        "This version uses OpenCV for frame-by-frame video processing and FFMPEG for fast audio mixing and final video creation.")
    video_params_state = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            main_video_input = gr.Video(label="1. Upload Main Video")
            gdrive_url_main = gr.Textbox(label="Or, Google Drive URL for Main Video",
                                         placeholder="Enter Google Drive File URL", lines=1)
            gdrive_main_btn = gr.Button("Download Main Video from URL")
            main_video_status = gr.Textbox(label="Download Status", interactive=False, visible=False)
        with gr.Column(scale=1):
            avatar_file_input = gr.File(label="2. Upload Avatar Videos", file_count="multiple", file_types=["video"],
                                        type="filepath")
            gdrive_url_avatar = gr.Textbox(label="Or, Google Drive URL for Avatars",
                                           placeholder="Enter Google Drive Folder URL", lines=1)
            gdrive_avatar_btn = gr.Button("Download Avatars from Folder URL")
            avatar_folder_status = gr.Textbox(label="Download Status", interactive=False, visible=False)
    with gr.Row(equal_height=True):
        with gr.Column(scale=2):
            gr.Markdown("### 3. Generate Previews & Videos")
            preview_btn = gr.Button("Generate Previews", variant="secondary")
            parallel_mode_checkbox = gr.Checkbox(label="Parallel Mode (Avatar and main video play at the same time)",
                                                 value=True)
            generate_btn = gr.Button("Generate Final Videos", variant="primary")

    with gr.Tabs():
        with gr.TabItem("Previews"):
            generated_previews_gallery = gr.Gallery(label="Generated Previews", columns=6, object_fit="contain",
                                                    height="auto")
        with gr.TabItem("Final Videos"):
            generated_videos_output = gr.Gallery(label="Generated Videos", columns=4, object_fit="contain",
                                                 height="auto", allow_preview=True)
            download_all_btn = gr.DownloadButton("Download All as ZIP", variant="primary", visible=False)

    preview_btn.click(fn=generate_all_previews, inputs=[main_video_input, avatar_file_input],
                      outputs=[generated_previews_gallery, video_params_state])
    generate_btn.click(fn=generate_videos,
                       inputs=[main_video_input, avatar_file_input, video_params_state, parallel_mode_checkbox],
                       outputs=[generated_videos_output, download_all_btn])
    download_all_btn.click(fn=zip_videos, inputs=[generated_videos_output], outputs=download_all_btn)
    gdrive_main_btn.click(fn=download_gdrive_file_for_single_mode, inputs=[gdrive_url_main],
                          outputs=[main_video_input, main_video_status])
    gdrive_avatar_btn.click(fn=download_gdrive_folder, inputs=[gdrive_url_avatar],
                            outputs=[avatar_file_input, avatar_folder_status])

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    for folder in ["generated_videos", "generated_previews", "downloaded_avatar_folders", "downloaded_files"]:
        dir_to_clean = script_dir / folder
        if dir_to_clean.exists():
            shutil.rmtree(dir_to_clean)
    demo.launch(server_name="0.0.0.0", server_port=7864)
