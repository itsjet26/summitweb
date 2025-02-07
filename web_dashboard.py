from flask import Flask, redirect

app = Flask(__name__)

def get_facefusion_url():
    return read_url_from_file("/workspace/facefusion_url.txt", "http://localhost:7860")

def get_video_retalker_url():
    return read_url_from_file("/workspaace/video_retalker_url.txt", "http://localhost:5001")

def read_url_from_file(file_path, fallback_url):
    """ Read the URL from the file and return it, else return a fallback URL """
    for _ in range(10):
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                url = file.read().strip()
                if "https://" in url:
                    return url
        time.sleep(2)
    return fallback_url

@app.route('/')
def home():
    programs = {
        "FaceFusion": get_facefusion_url(),
        "Video-Retalker": get_video_retalker_url(),
        "RVC (Voice Conversion)": "http://localhost:7897",
    }
    
    buttons = "".join([f'<a href="{url}" target="_blank"><button>{name}</button></a><br>' for name, url in programs.items()])
    return f"<h1>Program Dashboard</h1>{buttons}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
