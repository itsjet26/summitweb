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
    try:
        if not gdrive_url:
            return None, gr.update(value="Please provide a Google Drive Folder URL.", visible=True)

        with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as temp_dir:
            temp_dir_path = Path(temp_dir)
            progress(0.1, desc="Starting folder download")

            output_dir = str(temp_dir_path / "avatar_folder")
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            gdown.download_folder(
                gdrive_url,
                output=output_dir,
                quiet=False,
                use_cookies=True,
                remaining_ok=True
            )

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
                return None, gr.update(value="No valid video files found in the downloaded folder.", visible=True)

            script_dir = Path(__file__).parent
            persistent_dir = script_dir / "downloaded_avatar_folders"
            if persistent_dir.exists():
                shutil.rmtree(persistent_dir)
            persistent_dir.mkdir(parents=True, exist_ok=True)

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

    avatar_videos_list = [Path(f) for f in avatar_file_paths if Path(f).is_file()]
    if not avatar_videos_list:
        gr.Warning("No valid avatar video files found for previews.")
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

    for avatar_video_path in progress.tqdm(avatar_videos_list, desc="Generating Previews"):
        try:
            avatar_cap = cv2.VideoCapture(str(avatar_video_path))
            if not avatar_cap.isOpened(): continue
            ret_avatar, avatar_frame = avatar_cap.read()
            avatar_cap.release()
            if not ret_avatar: continue

            zoom_factor = random.uniform(1.0, 1.2)
            cropped_width = int(main_w / zoom_factor)
            cropped_height = int(main_h / zoom_factor)
            crop_x = random.randint(0, main_w - cropped_width)
            crop_y = random.randint(0, main_h - cropped_height)
            processed_main_frame = initial_main_frame_raw[crop_y:crop_y + cropped_height, crop_x:crop_x + cropped_width]
            processed_main_frame = cv2.resize(processed_main_frame, (main_w, main_h), interpolation=cv2.INTER_AREA)

            target_avatar_height = random.uniform(main_h / 4, main_h / 3)
            avatar_aspect_ratio = avatar_frame.shape[1] / avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)
            resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                              interpolation=cv2.INTER_AREA)

            # --- EDGE-TOUCHING PLACEMENT LOGIC FOR PREVIEWS ---
            placement_zone = random.choice(["left_vertical", "bottom_horizontal", "top_right_vertical"])

            if placement_zone == "left_vertical":
                x_pos = 0
                y_pos = random.randint(0, main_h - scaled_avatar_h)
            elif placement_zone == "bottom_horizontal":
                # Only allow placement in the left half of the bottom bar
                right_boundary = (main_w // 2) - scaled_avatar_w
                x_pos = random.randint(0, max(0, right_boundary))
                y_pos = main_h - scaled_avatar_h
            elif placement_zone == "top_right_vertical":
                x_pos = main_w - scaled_avatar_w
                # Constrain to the top half to match the drawing
                y_boundary = (main_h // 2) - scaled_avatar_h
                y_pos = random.randint(0, max(0, y_boundary))

            x_pos = max(0, min(x_pos, main_w - scaled_avatar_w))
            y_pos = max(0, min(y_pos, main_h - scaled_avatar_h))

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


# Function to generate final videos
def generate_videos(main_video_path, avatar_file_paths, progress=gr.Progress()):
    if not main_video_path or not avatar_file_paths:
        gr.Warning("Please upload both a main video and avatar video files.")
        return []

    script_dir = Path(__file__).parent
    video_output_dir = script_dir / "generated_videos"
    video_output_dir.mkdir(parents=True, exist_ok=True)

    avatar_videos_list = [Path(f) for f in avatar_file_paths if Path(f).is_file()]
    if not avatar_videos_list:
        gr.Warning("No valid avatar video files found.")
        return []

    generated_video_paths = []

    main_cap_initial = cv2.VideoCapture(str(main_video_path))
    if not main_cap_initial.isOpened():
        gr.Warning(f"Could not open main video: {main_video_path}")
        return []

    fps = main_cap_initial.get(cv2.CAP_PROP_FPS)
    main_width = int(main_cap_initial.get(cv2.CAP_PROP_FRAME_WIDTH))
    main_height = int(main_cap_initial.get(cv2.CAP_PROP_FRAME_HEIGHT))

    ret_first, first_main_frame_raw = main_cap_initial.read()
    main_cap_initial.release()
    if not ret_first:
        gr.Warning("Could not read the first frame from the main video.")
        return []

    for avatar_video_path in progress.tqdm(avatar_videos_list, desc="Generating Videos"):
        try:
            zoom_factor = random.uniform(1.0, 1.2)
            cropped_width = int(main_width / zoom_factor)
            cropped_height = int(main_height / zoom_factor)
            crop_x = random.randint(0, main_width - cropped_width)
            crop_y = random.randint(0, main_height - cropped_height)

            frozen_main_frame_processed = first_main_frame_raw[crop_y:crop_y + cropped_height,
                                          crop_x:crop_x + cropped_width]
            frozen_main_frame_processed = cv2.resize(frozen_main_frame_processed, (main_width, main_height),
                                                     interpolation=cv2.INTER_AREA)

            avatar_cap = cv2.VideoCapture(str(avatar_video_path))
            if not avatar_cap.isOpened(): continue
            avatar_frame_count = int(avatar_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            ret_avatar, temp_avatar_frame = avatar_cap.read()
            if not ret_avatar:
                avatar_cap.release()
                continue
            avatar_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            target_avatar_height = random.uniform(main_height / 4, main_height / 3)
            avatar_aspect_ratio = temp_avatar_frame.shape[1] / temp_avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)

            # --- EDGE-TOUCHING PLACEMENT LOGIC FOR FINAL VIDEOS ---
            placement_zone = random.choice(["left_vertical", "bottom_horizontal", "top_right_vertical"])

            if placement_zone == "left_vertical":
                x_pos = 0
                y_pos = random.randint(0, main_height - scaled_avatar_h)
            elif placement_zone == "bottom_horizontal":
                # Only allow placement in the left half of the bottom bar
                right_boundary = (main_width // 2) - scaled_avatar_w
                x_pos = random.randint(0, max(0, right_boundary))
                y_pos = main_height - scaled_avatar_h
            elif placement_zone == "top_right_vertical":
                x_pos = main_width - scaled_avatar_w
                # Constrain to the top half to match the drawing
                y_boundary = (main_height // 2) - scaled_avatar_h
                y_pos = random.randint(0, max(0, y_boundary))

            x_pos = max(0, min(x_pos, main_width - scaled_avatar_w))
            y_pos = max(0, min(y_pos, main_height - scaled_avatar_h))

            output_filename = f"generated_{avatar_video_path.stem}.mp4"
            output_path = video_output_dir / output_filename
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (main_width, main_height))

            # Part 1: Play avatar video over the frozen, processed main video frame
            for _ in range(avatar_frame_count):
                ret_avatar, avatar_frame = avatar_cap.read()
                if not ret_avatar: break
                resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                                  interpolation=cv2.INTER_AREA)
                avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)
                composite_frame = overlay_alpha(frozen_main_frame_processed.copy(), avatar_rgba, x_pos, y_pos)
                out.write(composite_frame)
            avatar_cap.release()

            # Part 2: Play the full main video from the beginning
            main_cap_replay = cv2.VideoCapture(str(main_video_path))
            while True:
                ret_main, main_frame_raw_replay = main_cap_replay.read()
                if not ret_main: break
                processed_main_frame_replay = main_frame_raw_replay[crop_y:crop_y + cropped_height,
                                              crop_x:crop_x + cropped_width]
                processed_main_frame_replay = cv2.resize(processed_main_frame_replay, (main_width, main_height),
                                                         interpolation=cv2.INTER_AREA)
                out.write(processed_main_frame_replay)
            main_cap_replay.release()

            out.release()
            generated_video_paths.append(str(output_path))

        except Exception as e:
            print(f"Error generating video for {avatar_video_path}: {e}")
            print(traceback.format_exc())
            continue

    return generated_video_paths


# Gradio UI setup
with gr.Blocks(title="Talking Head Avatar Overlay App") as demo:
    gr.Markdown("# Talking Head Avatar Overlay App")
    gr.Markdown(
        "Upload a main video and avatar videos. The avatar will be placed on a frozen frame of the main video, which will play after the avatar is finished.")

    with gr.Row():
        with gr.Column(scale=1):
            main_video_input = gr.Video(label="Upload Main Video")
            gdrive_url_main = gr.Textbox(label="Or, Google Drive URL for Main Video",
                                         placeholder="Enter Google Drive File URL", lines=1)
            gdrive_main_btn = gr.Button("Download Main Video from URL")
            main_video_status = gr.Textbox(label="Download Status", interactive=False, visible=False)

        with gr.Column(scale=1):
            avatar_file_input = gr.File(
                label="Upload Avatar Video Files (with green screen)",
                file_count="multiple",
                file_types=["video"],
                type="filepath"
            )
            gdrive_url_avatar = gr.Textbox(label="Or, Google Drive URL for Avatar Videos Folder",
                                           placeholder="Enter Google Drive Folder URL", lines=1)
            gdrive_avatar_btn = gr.Button("Download Avatars from Folder URL")
            avatar_folder_status = gr.Textbox(label="Download Status", interactive=False, visible=False)

    with gr.Row():
        preview_btn = gr.Button("Generate Previews", variant="secondary")
        generate_btn = gr.Button("Generate Final Videos", variant="primary")

    with gr.Column():
        gr.Markdown("## Previews")
        gr.Markdown(
            "Previews show a single frame with randomized placement touching the screen edges in your specified zones.")
        generated_previews_gallery = gr.Gallery(label="Generated Previews", columns=4, object_fit="contain",
                                                height="auto")

        gr.Markdown("## Generated Videos")
        gr.Markdown("Final videos are listed below. Click to download or view.")
        generated_videos_output = gr.File(
            label="Generated Video Files",
            file_count="multiple",
            interactive=False
        )

    # --- Button Click Actions ---
    preview_btn.click(
        fn=generate_all_previews,
        inputs=[main_video_input, avatar_file_input],
        outputs=generated_previews_gallery
    )

    generate_btn.click(
        fn=generate_videos,
        inputs=[main_video_input, avatar_file_input],
        outputs=generated_videos_output
    )

    gdrive_main_btn.click(
        fn=download_gdrive_file_for_single_mode,
        inputs=[gdrive_url_main],
        outputs=[main_video_input, main_video_status]
    )

    gdrive_avatar_btn.click(
        fn=download_gdrive_folder,
        inputs=[gdrive_url_avatar],
        outputs=[avatar_file_input, avatar_folder_status]
    )

demo.launch(server_name="0.0.0.0", server_port=7864)
