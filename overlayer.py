import gradio as gr
import cv2
import numpy as np
import os
import tempfile
import random
import gdown
from pathlib import Path
import re
import time
import zipfile
import shutil


# Function to remove green background and return a 4-channel (RGBA) image
def remove_green_background_with_alpha(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    alpha_channel = cv2.bitwise_not(mask)
    b, g, r = cv2.split(frame)
    rgba_frame = cv2.merge([b, g, r, alpha_channel])
    return rgba_frame


# Function to overlay a foreground image (with alpha channel) onto a background image
def overlay_alpha(background, foreground_rgba, x, y):
    fg_h, fg_w = foreground_rgba.shape[:2]
    bg_h, bg_w = background.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(bg_w, x + fg_w), min(bg_h, y + fg_h)

    fg_x1 = x1 - x
    fg_y1 = y1 - y
    fg_x2 = x2 - x
    fg_y2 = y2 - y

    if x2 <= x1 or y2 <= y1:
        return background

    fg_crop = foreground_rgba[fg_y1:fg_y2, fg_x1:fg_x2]
    b, g, r, alpha = cv2.split(fg_crop)
    alpha_normalized = alpha / 255.0
    alpha_fg_3_channel = cv2.merge([alpha_normalized, alpha_normalized, alpha_normalized])
    foreground_rgb_part = cv2.merge([b, g, r])
    bg_roi = background[y1:y2, x1:x2]
    composite = (foreground_rgb_part * alpha_fg_3_channel + bg_roi * (1 - alpha_fg_3_channel)).astype(np.uint8)
    background[y1:y2, x1:x2] = composite
    return background


# Google Drive URL conversion function (for individual files)
def convert_gdrive_url_for_single_mode(gdrive_url):
    try:
        file_id_match = re.search(r'[-\w]{25,}(?=/|$)', gdrive_url)
        if not file_id_match: return None
        file_id = file_id_match.group(0)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return None


# Function to download a single Google Drive file (e.g., main video)
def download_gdrive_file_for_single_mode(gdrive_url):
    """
    Download function that returns the file path for a single video.
    Forces the downloaded video file to have a .mp4 extension.
    """
    try:
        if not gdrive_url:
            return None, gr.update(value="Please provide a Google Drive URL", visible=True)

        direct_url = convert_gdrive_url_for_single_mode(gdrive_url)
        if not direct_url:
            return None, gr.update(value="Invalid Google Drive URL.", visible=True)

        script_dir = Path(__file__).parent
        download_dir = script_dir / "downloaded_files"
        download_dir.mkdir(parents=True, exist_ok=True)

        temp_basename = f"gdown_single_temp_{os.urandom(4).hex()}"
        target_path_for_gdown = download_dir / temp_basename

        final_downloaded_path = gdown.download(direct_url, quiet=False, output=str(target_path_for_gdown))
        temp_file_path = Path(final_downloaded_path)

        if not temp_file_path.exists() or temp_file_path.stat().st_size == 0:
            return None, gr.update(value="Download failed: File is empty or does not exist.", visible=True)

        new_file_path = temp_file_path.with_suffix('.mp4')
        if temp_file_path != new_file_path:
            os.rename(temp_file_path, new_file_path)

        return str(new_file_path), gr.update(value=f"File downloaded as {new_file_path.name}", visible=True)

    except Exception as e:
        print(f"Error in download_gdrive_file_for_single_mode: {e}")
        return None, gr.update(value=f"Error downloading file: {str(e)}", visible=True)


# Function to download a Google Drive folder into a temp folder
def download_gdrive_folder(gdrive_url, progress=gr.Progress()):
    """
    Downloads a Google Drive folder into a temporary directory and returns a list of video file paths.
    Forces all video files to .mp4 extension.
    """
    try:
        if not gdrive_url:
            return None, gr.update(value="Please provide a Google Drive Folder URL.", visible=True)

        # Create a temporary directory
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as temp_dir:
            temp_dir_path = Path(temp_dir)
            progress(0.1, desc="Starting folder download")

            # Download the folder to the temporary directory
            output_dir = str(temp_dir_path / "avatar_folder")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            print(f"Downloading to: {output_dir}")  # Debug print

            # Download the folder
            downloaded_files = gdown.download_folder(
                gdrive_url,
                output=output_dir,
                quiet=False,
                use_cookies=True,
                remaining_ok=True
            )
            print(f"Downloaded files: {downloaded_files}")  # Debug print

            # Use output_dir as the downloaded folder path
            downloaded_folder_path = Path(output_dir)

            if not downloaded_folder_path.exists() or not downloaded_folder_path.is_dir():
                return None, gr.update(value="Folder download failed or folder is empty.", visible=True)

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
                            print(f"Error renaming {file_path} to {new_file_path}: {e}")
                            continue
                    video_files_list.append(new_file_path)

            if not video_files_list:
                return None, gr.update(value="No valid video files found in the downloaded Google Drive folder.",
                                       visible=True)

            # Create a persistent directory to hold the files for Gradio
            script_dir = Path(__file__).parent
            persistent_dir = script_dir / "downloaded_avatar_folders"
            if persistent_dir.exists():
                shutil.rmtree(persistent_dir)
            persistent_dir.mkdir(parents=True, exist_ok=True)

            # Copy files to persistent_dir and collect their paths
            persistent_file_paths = []
            for file_path in video_files_list:
                dest_path = persistent_dir / file_path.name
                shutil.copy(file_path, dest_path)
                persistent_file_paths.append(str(dest_path))

            progress(1.0, desc="Folder download and processing complete")
            return persistent_file_paths, gr.update(value=f"Downloaded {len(persistent_file_paths)} video files.",
                                                    visible=True)

    except Exception as e:
        print(f"Error downloading Google Drive folder: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, gr.update(value=f"Error downloading folder: {str(e)}", visible=True)


# Function to generate previews for each avatar video
def generate_all_previews(main_video_path, avatar_file_paths, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Please upload both a main video and avatar video files for previews.")
        return []

    script_dir = Path(__file__).parent
    preview_output_dir = script_dir / "generated_previews"
    preview_output_dir.mkdir(parents=True, exist_ok=True)

    avatar_videos_list = [
        Path(f_path) for f_path in avatar_file_paths
        if Path(f_path).is_file() and Path(f_path).suffix.lower() in ('.mp4', '.avi', '.mov', '.webm', '.flv', '.wmv')
    ]

    if not avatar_videos_list:
        gr.Warning("No valid video files found in the provided avatar source for previews.")
        return []

    preview_paths = []

    main_cap_temp = cv2.VideoCapture(str(main_video_path))
    if not main_cap_temp.isOpened():
        gr.Warning(f"Could not open main video: {main_video_path}")
        return []

    ret_main, initial_main_frame_raw = main_cap_temp.read()
    main_cap_temp.release()
    if not ret_main:
        gr.Warning("Could not read first frame from main video for previews.")
        return []

    main_h, main_w = initial_main_frame_raw.shape[:2]

    # Define safe zones (25% of width for vertical, 25% of height for horizontal)
    safe_width = int(main_w * 0.25)  # Left vertical strip
    safe_height = int(main_h * 0.25)  # Bottom horizontal strip

    for avatar_video_path in progress.tqdm(avatar_videos_list, desc="Generating Previews"):
        try:
            avatar_cap = cv2.VideoCapture(str(avatar_video_path))
            if not avatar_cap.isOpened():
                print(f"Warning: Could not open avatar video {avatar_video_path}. Skipping.")
                continue

            ret_avatar, avatar_frame = avatar_cap.read()
            avatar_cap.release()
            if not ret_avatar:
                print(f"Warning: Could not read first frame from avatar video {avatar_video_path}. Skipping.")
                continue

            zoom_factor = random.uniform(1.0, 1.2)
            cropped_width = int(main_w / zoom_factor)
            cropped_height = max(1, min(int(main_h / zoom_factor), main_h))
            cropped_width = max(1, min(cropped_width, main_w))
            crop_x = random.randint(0, max(0, main_w - cropped_width))
            crop_y = random.randint(0, max(0, main_h - cropped_height))

            processed_main_frame = initial_main_frame_raw[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width]
            processed_main_frame = cv2.resize(processed_main_frame, (main_w, main_h), interpolation=cv2.INTER_AREA)

            target_avatar_h_min = main_h / 4
            target_avatar_h_max = main_h / 3
            target_avatar_height = random.uniform(target_avatar_h_min, target_avatar_h_max)
            avatar_aspect_ratio = avatar_frame.shape[1] / avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)
            scaled_avatar_w = max(1, scaled_avatar_w)
            scaled_avatar_h = max(1, scaled_avatar_h)

            # Resize the avatar frame
            resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                              interpolation=cv2.INTER_AREA)

            # Restrict placement to "L" shaped safe zones
            edge_choice = random.choice(["left", "bottom"])
            x_pos, y_pos = 0, 0

            if edge_choice == "left":
                x_pos = 0  # Left edge
                y_pos = random.randint(0, main_h - scaled_avatar_h)  # Full height
            elif edge_choice == "bottom":
                x_pos = 0  # Start from left
                y_pos = main_h - safe_height  # Bottom 25% height
                if y_pos + scaled_avatar_h > main_h:
                    y_pos = main_h - scaled_avatar_h  # Ensure it fits

            # Ensure avatar fits within safe zones
            if x_pos + scaled_avatar_w > safe_width:
                x_pos = safe_width - scaled_avatar_w
            if y_pos < 0:
                y_pos = 0

            avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)
            composite_frame = overlay_alpha(processed_main_frame.copy(), avatar_rgba, x_pos, y_pos)

            preview_filename = f"preview_{avatar_video_path.stem}.png"
            preview_path = preview_output_dir / preview_filename
            cv2.imwrite(str(preview_path), composite_frame)
            preview_paths.append(str(preview_path))

        except Exception as e:
            print(f"Error generating preview for {avatar_video_path}: {e}")
            continue

    return preview_paths


# Function to generate final videos (with overlays)
def generate_videos(main_video_path, avatar_file_paths, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Please upload both a main video and avatar video files for final video generation.")
        return []

    script_dir = Path(__file__).parent
    video_output_dir = script_dir / "generated_videos"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    avatar_videos_list = [
        Path(f_path) for f_path in avatar_file_paths
        if Path(f_path).is_file() and Path(f_path).suffix.lower() in ('.mp4', '.avi', '.mov', '.webm', '.flv', '.wmv')
    ]

    if not avatar_videos_list:
        gr.Warning("No valid video files found in the provided avatar source for final videos.")
        return []

    generated_video_paths = []

    main_cap = cv2.VideoCapture(str(main_video_path))
    if not main_cap.isOpened():
        gr.Warning(f"Could not open main video: {main_video_path}")
        return []

    fps = main_cap.get(cv2.CAP_PROP_FPS)
    main_width = int(main_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    main_height = int(main_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Define safe zones (25% of width for vertical, 25% of height for horizontal)
    safe_width = int(main_width * 0.25)  # Left vertical strip
    safe_height = int(main_height * 0.25)  # Bottom horizontal strip

    for avatar_video_path in progress.tqdm(avatar_videos_list, desc="Generating Videos"):
        try:
            output_filename = f"generated_{avatar_video_path.stem}.mp4"
            output_path = video_output_dir / output_filename

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (main_width, main_height))

            avatar_cap = cv2.VideoCapture(str(avatar_video_path))
            if not avatar_cap.isOpened():
                print(f"Warning: Could not open avatar video {avatar_video_path}. Skipping.")
                out.release()
                continue

            ret_avatar, temp_avatar_frame = avatar_cap.read()
            if not ret_avatar:
                print(f"Warning: Could not read first frame from avatar video {avatar_video_path}. Skipping.")
                avatar_cap.release()
                out.release()
                continue

            zoom_factor = random.uniform(1.0, 1.15)
            cropped_width = int(main_width / zoom_factor)
            cropped_height = max(1, min(int(main_height / zoom_factor), main_height))
            cropped_width = max(1, min(cropped_width, main_width))
            crop_x = random.randint(0, max(0, main_width - cropped_width))
            crop_y = random.randint(0, max(0, main_height - cropped_height))

            target_avatar_h_min = main_height / 4
            target_avatar_h_max = main_height / 3
            target_avatar_height = random.uniform(target_avatar_h_min, target_avatar_h_max)
            avatar_aspect_ratio = temp_avatar_frame.shape[1] / temp_avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)
            scaled_avatar_w = max(1, scaled_avatar_w)
            scaled_avatar_h = max(1, scaled_avatar_h)

            # Resize the avatar frame
            resized_avatar_frame = cv2.resize(temp_avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                              interpolation=cv2.INTER_AREA)

            # Restrict placement to "L" shaped safe zones
            edge_choice = random.choice(["left", "bottom"])
            x_pos, y_pos = 0, 0

            if edge_choice == "left":
                x_pos = 0  # Left edge
                y_pos = random.randint(0, main_height - scaled_avatar_h)  # Full height
            elif edge_choice == "bottom":
                x_pos = 0  # Start from left
                y_pos = main_height - safe_height  # Bottom 25% height
                if y_pos + scaled_avatar_h > main_height:
                    y_pos = main_height - scaled_avatar_h  # Ensure it fits

            # Ensure avatar fits within safe zones
            if x_pos + scaled_avatar_w > safe_width:
                x_pos = safe_width - scaled_avatar_w
            if y_pos < 0:
                y_pos = 0

            main_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            while True:
                ret_main, main_frame_raw = main_cap.read()
                ret_avatar, avatar_frame = avatar_cap.read()

                if not ret_main:
                    break

                if not ret_avatar:
                    avatar_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret_avatar, avatar_frame = avatar_cap.read()
                    if not ret_avatar:
                        break

                processed_main_frame = main_frame_raw[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width]
                processed_main_frame = cv2.resize(processed_main_frame, (main_width, main_height),
                                                  interpolation=cv2.INTER_AREA)

                resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                                  interpolation=cv2.INTER_AREA)
                avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)

                composite_frame = overlay_alpha(processed_main_frame.copy(), avatar_rgba, x_pos, y_pos)
                out.write(composite_frame)

            avatar_cap.release()
            out.release()
            generated_video_paths.append(str(output_path))

        except Exception as e:
            print(f"Error generating video for {avatar_video_path}: {e}")
            continue
    main_cap.release()
    return generated_video_paths


# Gradio UI setup
with gr.Blocks(title="Talking Head Avatar Overlay App") as demo:
    gr.Markdown("# Talking Head Avatar Overlay App")
    gr.Markdown(
        "Upload a main video and avatar video files (with green screen), or provide a Google Drive URL for both.")

    with gr.Row():
        with gr.Column():
            main_video_input = gr.Video(label="Upload Main Video (MP4, AVI, MOV, WEBM)")
            gdrive_url_main = gr.Textbox(label="Google Drive URL for Main Video", placeholder="Enter Google Drive URL",
                                         lines=1)
            gdrive_main_btn = gr.Button("Submit Main Video URL")
            main_video_status = gr.Textbox(label="Main Video Download Status", interactive=False, visible=False)

        with gr.Column():
            avatar_file_input = gr.File(
                label="Upload Avatar Video Files (MP4, AVI, MOV, WEBM)",
                file_count="multiple",
                file_types=[".mp4", ".avi", ".mov", ".webm", ".flv", ".wmv"],
                type="filepath"
            )
            gdrive_url_avatar = gr.Textbox(label="Google Drive URL for Avatar Videos Folder",
                                           placeholder="Enter Google Drive URL for a Folder", lines=1)
            gdrive_avatar_btn = gr.Button("Submit Avatar Folder URL")
            avatar_folder_status = gr.Textbox(label="Avatar Files Download Status", interactive=False, visible=False)

    with gr.Row():
        preview_btn = gr.Button("Generate Previews with Randomizations")
        generate_btn = gr.Button("Generate Overlay Videos")

    with gr.Column():
        gr.Markdown("## Previews")
        generated_previews_gallery = gr.Gallery(label="Generated Video Previews", columns=3, object_fit="contain",
                                                value=[])

        gr.Markdown("## Generated Videos")
        generated_videos_gallery = gr.Gallery(label="Generated Videos", columns=1, object_fit="contain", value=[])

    preview_btn.click(fn=generate_all_previews, inputs=[main_video_input, avatar_file_input],
                      outputs=generated_previews_gallery)
    generate_btn.click(fn=generate_videos, inputs=[main_video_input, avatar_file_input],
                       outputs=generated_videos_gallery)

    gdrive_main_btn.click(fn=download_gdrive_file_for_single_mode,
                          inputs=[gdrive_url_main],
                          outputs=[main_video_input, main_video_status])

    gdrive_avatar_btn.click(fn=download_gdrive_folder,
                            inputs=[gdrive_url_avatar],
                            outputs=[avatar_file_input, avatar_folder_status])

demo.launch(server_name="0.0.0.0", server_port=7864)
