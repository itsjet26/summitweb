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


# Google Drive URL conversion function
def convert_gdrive_url_for_single_mode(gdrive_url):
    try:
        file_id_match = re.search(r'[-\w]{25,}(?=/|$)', gdrive_url)
        if not file_id_match: return None
        file_id = file_id_match.group(0)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return None


# Modified Google Drive file download function to return only the path
def download_gdrive_file_for_single_mode(gdrive_url):
    """Download function that returns the file path or None, and a status message."""
    try:
        if not gdrive_url:
            return None, gr.update(value="Please provide a Google Drive URL", visible=True)

        # Get the direct download URL
        direct_url = convert_gdrive_url_for_single_mode(gdrive_url)
        if not direct_url:
            return None, gr.update(value="Invalid Google Drive URL.", visible=True)

        # Create a temporary directory for storing the downloaded file
        temp_dir = Path(tempfile.gettempdir())

        # Use gdown to download the file
        temp_file_path = gdown.download(direct_url, quiet=False, output=str(temp_dir))

        # Wait for the file to finish downloading and ensure it's not empty
        if temp_file_path and os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
            # Ensure the file is renamed correctly if it was downloaded as a .part
            if temp_file_path.endswith('.part'):
                final_file_path = temp_file_path.replace('.part', '.mp4')
                os.rename(temp_file_path, final_file_path)
                return final_file_path, gr.update(value=f"File downloaded as {os.path.basename(final_file_path)}",
                                                  visible=True)
            return temp_file_path, gr.update(value=f"File downloaded as {os.path.basename(temp_file_path)}",
                                             visible=True)

        return None, gr.update(value="Download failed.", visible=True)

    except Exception as e:
        return None, gr.update(value=f"Error downloading file: {str(e)}", visible=True)


# Function to generate previews for each avatar video
def generate_all_previews(main_video_path, avatar_folder_path, progress=gr.Progress()):
    if not main_video_path or not avatar_folder_path:
        gr.Warning("Please upload both a main video and an avatar videos folder for previews.")
        return []

    avatar_videos_list = [f_path for f_path in avatar_folder_path if
                          f_path.lower().endswith(('.mp4', '.avi', '.mov', '.webm'))]

    if not avatar_videos_list:
        gr.Warning("No valid video files found in the uploaded folder for previews.")
        return []

    preview_paths = []
    temp_dir = tempfile.mkdtemp()

    main_cap_temp = cv2.VideoCapture(main_video_path)
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
            avatar_cap = cv2.VideoCapture(avatar_video_path)
            if not avatar_cap.isOpened():
                print(f"Warning: Could not open avatar video {avatar_video_path}. Skipping.")
                continue

            ret_avatar, avatar_frame = avatar_cap.read()
            avatar_cap.release()
            if not ret_avatar:
                print(f"Warning: Could not read first frame from avatar video {avatar_video_path}. Skipping.")
                continue

            zoom_factor = random.uniform(1.0, 1.3)
            cropped_width = int(main_w / zoom_factor)
            cropped_height = int(main_h / zoom_factor)
            cropped_width = max(1, min(cropped_width, main_w))
            cropped_height = max(1, min(cropped_height, main_h))
            crop_x_start = random.randint(0, main_w - cropped_width) if (main_w - cropped_width) > 0 else 0
            crop_y_start = random.randint(0, main_h - cropped_height) if (main_h - cropped_height) > 0 else 0

            processed_main_frame = initial_main_frame_raw[crop_y_start: crop_y_start + cropped_height,
                                   crop_x_start: crop_x_start + cropped_width]
            processed_main_frame = cv2.resize(processed_main_frame, (main_w, main_h), interpolation=cv2.INTER_AREA)

            target_avatar_h_min = main_h / 8
            target_avatar_h_max = main_h / 6
            target_avatar_height = random.uniform(target_avatar_h_min, target_avatar_h_max)
            avatar_aspect_ratio = avatar_frame.shape[1] / avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)
            scaled_avatar_w = max(1, scaled_avatar_w)
            scaled_avatar_h = max(1, scaled_avatar_h)

            resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                              interpolation=cv2.INTER_AREA)

            edge_choice = random.choice(["top", "bottom", "left", "right"])
            x_pos, y_pos = 0, 0

            if edge_choice == "left":
                x_pos = 0
                y_pos = random.randint(0, max(0, main_h - scaled_avatar_h))
            elif edge_choice == "right":
                x_pos = main_w - scaled_avatar_w
                y_pos = random.randint(0, max(0, main_h - scaled_avatar_h))
            elif edge_choice == "top":
                y_pos = 0
                x_pos = random.randint(0, max(0, main_w - scaled_avatar_w))
            elif edge_choice == "bottom":
                y_pos = main_h - scaled_avatar_h
                x_pos = random.randint(0, max(0, main_w - scaled_avatar_w))

            avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)
            composite_frame = overlay_alpha(processed_main_frame.copy(), avatar_rgba, x_pos, y_pos)

            preview_filename = f"preview_{os.path.splitext(os.path.basename(avatar_video_path))[0]}.png"
            preview_path = os.path.join(temp_dir, preview_filename)
            cv2.imwrite(preview_path, composite_frame)
            preview_paths.append(preview_path)

        except Exception as e:
            print(f"Error generating preview for {avatar_video_path}: {e}")
            continue

    return preview_paths


# Function to generate final videos (with overlays)
def generate_videos(main_video_path, avatar_folder_path, progress=gr.Progress()):
    if not main_video_path or not avatar_folder_path:
        gr.Warning("Please upload both a main video and an avatar videos folder for final video generation.")
        return []

    avatar_videos_list = [f_path for f_path in avatar_folder_path if
                          f_path.lower().endswith(('.mp4', '.avi', '.mov', '.webm'))]

    if not avatar_videos_list:
        gr.Warning("No valid video files found in the uploaded folder for final videos.")
        return []

    generated_video_paths = []
    temp_dir = tempfile.mkdtemp()

    main_cap = cv2.VideoCapture(main_video_path)
    if not main_cap.isOpened():
        gr.Warning(f"Could not open main video: {main_video_path}")
        return []

    fps = main_cap.get(cv2.CAP_PROP_FPS)
    main_width = int(main_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    main_height = int(main_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    main_total_frames = int(main_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for avatar_video_path in progress.tqdm(avatar_videos_list, desc="Generating Videos"):
        try:
            output_filename = f"generated_{os.path.splitext(os.path.basename(avatar_video_path))[0]}.mp4"
            output_path = os.path.join(temp_dir, output_filename)

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (main_width, main_height))

            avatar_cap = cv2.VideoCapture(avatar_video_path)
            if not avatar_cap.isOpened():
                print(f"Warning: Could not open avatar video {avatar_video_path}. Skipping.")
                out.release()
                continue

            # Randomize position and size for this avatar video once
            ret_avatar, temp_avatar_frame = avatar_cap.read()
            if not ret_avatar:
                print(f"Warning: Could not read first frame from avatar video {avatar_video_path}. Skipping.")
                avatar_cap.release()
                out.release()
                continue

            zoom_factor = random.uniform(1.0, 1.3)
            cropped_width = int(main_width / zoom_factor)
            cropped_height = int(main_height / zoom_factor)
            cropped_width = max(1, min(cropped_width, main_width))
            cropped_height = max(1, min(cropped_height, main_height))
            crop_x_start = random.randint(0, main_width - cropped_width) if (main_width - cropped_width) > 0 else 0
            crop_y_start = random.randint(0, main_height - cropped_height) if (main_height - cropped_height) > 0 else 0

            target_avatar_h_min = main_height / 8
            target_avatar_h_max = main_height / 6
            target_avatar_height = random.uniform(target_avatar_h_min, target_avatar_h_max)
            avatar_aspect_ratio = temp_avatar_frame.shape[1] / temp_avatar_frame.shape[0]
            scaled_avatar_h = int(target_avatar_height)
            scaled_avatar_w = int(scaled_avatar_h * avatar_aspect_ratio)
            scaled_avatar_w = max(1, scaled_avatar_w)
            scaled_avatar_h = max(1, scaled_avatar_h)

            edge_choice = random.choice(["top", "bottom", "left", "right"])
            x_pos, y_pos = 0, 0

            if edge_choice == "left":
                x_pos = 0
                y_pos = random.randint(0, max(0, main_height - scaled_avatar_h))
            elif edge_choice == "right":
                x_pos = main_width - scaled_avatar_w
                y_pos = random.randint(0, max(0, main_height - scaled_avatar_h))
            elif edge_choice == "top":
                y_pos = 0
                x_pos = random.randint(0, max(0, main_width - scaled_avatar_w))
            elif edge_choice == "bottom":
                y_pos = main_height - scaled_avatar_h
                x_pos = random.randint(0, max(0, main_width - scaled_avatar_w))

            frame_idx = 0
            while True:
                ret_main, main_frame_raw = main_cap.read()
                ret_avatar, avatar_frame = avatar_cap.read()

                if not ret_main:
                    break  # End of main video

                if not ret_avatar:
                    # Loop avatar video if it's shorter than the main video
                    avatar_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret_avatar, avatar_frame = avatar_cap.read()
                    if not ret_avatar:  # Should not happen if video is valid
                        break

                # Apply random zoom/crop to main frame
                processed_main_frame = main_frame_raw[crop_y_start: crop_y_start + cropped_height,
                                       crop_x_start: crop_x_start + cropped_width]
                processed_main_frame = cv2.resize(processed_main_frame, (main_width, main_height),
                                                  interpolation=cv2.INTER_AREA)

                # Resize and process avatar frame
                resized_avatar_frame = cv2.resize(avatar_frame, (scaled_avatar_w, scaled_avatar_h),
                                                  interpolation=cv2.INTER_AREA)
                avatar_rgba = remove_green_background_with_alpha(resized_avatar_frame)

                # Overlay
                composite_frame = overlay_alpha(processed_main_frame.copy(), avatar_rgba, x_pos, y_pos)
                out.write(composite_frame)
                frame_idx += 1

            main_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset main video for next avatar
            avatar_cap.release()
            out.release()
            generated_video_paths.append(output_path)

        except Exception as e:
            print(f"Error generating video for {avatar_video_path}: {e}")
            continue
    main_cap.release()  # Release main video capture after all avatars are processed
    return generated_video_paths


# Gradio UI setup with the new inputs
with gr.Blocks() as demo:
    gr.Markdown("# Talking Head Avatar Overlay App")
    gr.Markdown(
        "Upload a main video, a folder containing avatar videos (with green screen), or provide a Google Drive URL for both video and avatar files.")

    with gr.Row():
        with gr.Column():
            main_video_input = gr.Video(label="Upload Main Video (MP4, AVI, MOV, WEBM)")
            gdrive_url_main = gr.Textbox(label="Google Drive URL for Main Video", placeholder="Enter Google Drive URL",
                                         lines=1)
            gdrive_main_btn = gr.Button("Submit Main Video URL")
            main_video_status = gr.Textbox(label="Main Video Download Status", interactive=False, visible=False)

        with gr.Column():
            avatar_folder_input = gr.File(label="Upload Folder with Avatar Videos (MP4, AVI, MOV, WEBM)",
                                          file_count="directory", type="filepath")
            gdrive_url_avatar = gr.Textbox(label="Google Drive URL for Avatar Videos (Folder or Zipped Folder)",
                                           placeholder="Enter Google Drive URL", lines=1)
            gdrive_avatar_btn = gr.Button("Submit Avatar Folder URL")
            avatar_folder_status = gr.Textbox(label="Avatar Folder Download Status", interactive=False, visible=False)

    with gr.Row():
        preview_btn = gr.Button("Generate Previews with Randomizations")
        generate_btn = gr.Button("Generate Overlay Videos")

    with gr.Column():
        gr.Markdown("## Previews")
        generated_previews_gallery = gr.Gallery(label="Generated Video Previews", columns=3, object_fit="contain",
                                                value=[])

        gr.Markdown("## Generated Videos")
        generated_videos_gallery = gr.Gallery(label="Generated Videos", columns=1, object_fit="contain", value=[])

    preview_btn.click(fn=generate_all_previews, inputs=[main_video_input, avatar_folder_input],
                      outputs=generated_previews_gallery)
    generate_btn.click(fn=generate_videos, inputs=[main_video_input, avatar_folder_input],
                       outputs=generated_videos_gallery)

    # Updated click events for Google Drive buttons
    gdrive_main_btn.click(fn=download_gdrive_file_for_single_mode, inputs=[gdrive_url_main],
                          outputs=[main_video_input, main_video_status])
    gdrive_avatar_btn.click(fn=download_gdrive_file_for_single_mode, inputs=[gdrive_url_avatar],
                            outputs=[avatar_folder_input, avatar_folder_status])

demo.launch(server_name="0.0.0.0", server_port=7864)
