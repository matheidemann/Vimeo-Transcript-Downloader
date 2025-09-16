import customtkinter as ctk
import requests
import re
import os
import time
import json
from tkinter import filedialog, messagebox

# === CONFIGURATION ===
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'VimeoDownloader')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
DEFAULT_CONFIG = {
    "default_output_folder": os.path.join(os.path.expanduser("~"), "Desktop"),
    "default_filename_template": "{UNIX_TIMESTAMP}_TRANSCRIPT_{VIDEO_ID}.txt"
}

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.isfile(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

config = load_config()

# === MAIN FUNCTIONS ===
def fetch_video_info():
    vimeo_url = url_entry.get().strip()
    if not vimeo_url:
        messagebox.showerror("Error", "Please enter a Vimeo video URL.")
        return
    try:
        config_url = f"{vimeo_url}/config"
        response = requests.get(config_url)
        response.raise_for_status()
        config_json = response.json()

        video_title = config_json.get("video", {}).get("title", "Unknown Title")
        duration_seconds = int(config_json.get("video", {}).get("duration", 0))
        duration_formatted = time.strftime("%H:%M:%S", time.gmtime(duration_seconds))

        text_tracks = config_json.get("request", {}).get("text_tracks", [])
        if not text_tracks:
            raise ValueError("No subtitles found for this video.")

        languages_dict.clear()
        for track in text_tracks:
            languages_dict[track.get("label")] = track.get("lang")

        sorted_labels = sorted(languages_dict.keys())
        lang_option.configure(values=sorted_labels, state="normal")
        lang_option.set(sorted_labels[0])

        transcript_url = text_tracks[0].get("url")
        if transcript_url.startswith("/"):
            transcript_url = f"https://player.vimeo.com{transcript_url}"
        transcript_text = requests.get(transcript_url).text
        char_count = len(clean_transcript(transcript_text, remove_timestamps=True))

        # Update UI labels
        title_label.configure(text=f"🏷 Title: {video_title}")
        duration_label.configure(text=f"🕒 Duration: {duration_formatted}")
        languages_label.configure(text=f"🌐 Languages: {len(sorted_labels)}")
        chars_label.configure(text=f"🔤 Transcript (filtered) Characters: {char_count}")

        enable_config_widgets()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch video info:\n{str(e)}")

def clean_transcript(raw_text: str, remove_timestamps: bool) -> str:
    lines = raw_text.splitlines()
    cleaned_lines = [
        line.strip()
        for line in lines
        if line.strip() and
        (not remove_timestamps or (
            not line.isdigit() and
            not re.match(r"\d{2}:\d{2}:\d{2}\.\d{3} -->", line)
        ))
    ]
    # Add line breaks after each period
    return re.sub(r"\.\s*", ".\n", " ".join(cleaned_lines))

def choose_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_var.set(folder_selected)

def save_transcript():
    vimeo_url = url_entry.get().strip()
    selected_lang_label = lang_option.get()
    selected_lang_code = languages_dict[selected_lang_label]
    remove_ts = remove_timestamps_switch.get()
    output_folder = folder_var.get()
    filename_template = filename_entry.get().strip() or config["default_filename_template"]

    match = re.search(r"/video/(\d+)", vimeo_url)
    if not match:
        messagebox.showerror("Error", "Invalid Vimeo video URL format.")
        return

    video_id = match.group(1)
    timestamp = int(time.time())

    filename = filename_template.replace("{UNIX_TIMESTAMP}", str(timestamp)).replace("{VIDEO_ID}", video_id)
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    output_file = os.path.join(output_folder, filename)

    try:
        config_url = f"{vimeo_url}/config"
        config_json = requests.get(config_url).json()
        text_tracks = config_json.get("request", {}).get("text_tracks", [])
        track = next(t for t in text_tracks if t.get("lang") == selected_lang_code)

        transcript_url = track.get("url")
        if transcript_url.startswith("/"):
            transcript_url = f"https://player.vimeo.com{transcript_url}"

        transcript_text = requests.get(transcript_url).text
        cleaned_text = clean_transcript(transcript_text, remove_ts)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        messagebox.showinfo("Success", f"Transcript saved to:\n{output_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save transcript:\n{str(e)}")

def enable_config_widgets():
    remove_timestamps_switch.configure(state="normal")
    folder_button.configure(state="normal")
    filename_entry.configure(state="normal")
    download_button.configure(state="normal")

def open_settings_window():
    settings_window = ctk.CTkToplevel()
    settings_window.title("Settings")
    settings_window.geometry("450x250")
    settings_window.resizable(False, False)
    settings_window.attributes("-topmost", True)
    settings_window.focus_force()
    settings_window.grab_set()

    # Folder setting
    folder_label = ctk.CTkLabel(settings_window, text="Default output folder:")
    folder_label.pack(pady=(20, 5), padx=20, anchor="w")

    folder_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
    folder_frame.pack(pady=5, padx=20, fill="x")

    folder_entry = ctk.CTkEntry(folder_frame)
    folder_entry.insert(0, config["default_output_folder"])
    folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    def select_settings_folder():
        new_folder = filedialog.askdirectory()
        if new_folder:
            folder_entry.delete(0, "end")
            folder_entry.insert(0, new_folder)

    folder_button_settings = ctk.CTkButton(folder_frame, text="📂", width=40, command=select_settings_folder)
    folder_button_settings.pack(side="left")

    # Filename Template
    filename_label = ctk.CTkLabel(settings_window, text="Default filename template:")
    filename_label.pack(pady=(20, 5), padx=20, anchor="w")

    filename_entry_setting = ctk.CTkEntry(settings_window)
    filename_entry_setting.insert(0, config["default_filename_template"])
    filename_entry_setting.pack(pady=5, padx=20, fill="x")

    # Save button
    def save_settings():
        config["default_output_folder"] = folder_entry.get()
        config["default_filename_template"] = filename_entry_setting.get()
        save_config(config)
        settings_window.destroy()

    save_button = ctk.CTkButton(settings_window, text="Save Settings", command=save_settings)
    save_button.pack(pady=20)

# === GUI SETUP ===
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Vimeo Transcript Downloader")
app.geometry("850x770")
app.resizable(False, False)

languages_dict = {}

# ===== TITLE =====
title_label = ctk.CTkLabel(app, text="🎥 Vimeo Transcript Downloader", font=("Segoe UI", 26, "bold"))
title_label.pack(pady=(20, 10))

subtitle_label = ctk.CTkLabel(app, text="Download and customize subtitles easily", font=("Segoe UI", 16))
subtitle_label.pack(pady=(0, 15))

# ===== VIDEO URL =====
url_frame = ctk.CTkFrame(app, corner_radius=10)
url_frame.pack(pady=(10, 10), padx=20, fill="x")

ctk.CTkLabel(url_frame, text="Vimeo Video URL:", anchor="w").pack(pady=(10, 0), padx=10, fill="x")

inner_url_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
inner_url_frame.pack(pady=(5, 10), padx=10, fill="x")

url_entry = ctk.CTkEntry(inner_url_frame, placeholder_text="Paste Vimeo video link here")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

fetch_button = ctk.CTkButton(inner_url_frame, text="🔍 Fetch Video", command=fetch_video_info, width=120)
fetch_button.pack(side="left")

# ===== VIDEO INFO DISPLAY =====
video_info_frame = ctk.CTkFrame(app, corner_radius=10)
video_info_frame.pack(pady=(0, 15), padx=20, fill="x")

title_label = ctk.CTkLabel(video_info_frame, text="🏷 Title: —", font=("Segoe UI", 14), anchor="w")
title_label.pack(anchor="w", padx=10, pady=2)

duration_label = ctk.CTkLabel(video_info_frame, text="🕒 Duration: —", font=("Segoe UI", 14), anchor="w")
duration_label.pack(anchor="w", padx=10, pady=2)

languages_label = ctk.CTkLabel(video_info_frame, text="🌐 Languages: —", font=("Segoe UI", 14), anchor="w")
languages_label.pack(anchor="w", padx=10, pady=2)

chars_label = ctk.CTkLabel(video_info_frame, text="🔤 Transcript (filtered) Characters: —", font=("Segoe UI", 14), anchor="w")
chars_label.pack(anchor="w", padx=10, pady=2)

# ===== CONFIGURATION OPTIONS =====
settings_frame = ctk.CTkFrame(app, corner_radius=10)
settings_frame.pack(pady=(0, 15), padx=20, fill="x")

ctk.CTkLabel(settings_frame, text="Transcript Settings:", anchor="w").pack(pady=(10, 0), padx=10, fill="x")

lang_option = ctk.CTkOptionMenu(settings_frame, values=["Available Languages"], state="disabled")
lang_option.set("Available Languages")
lang_option.pack(pady=(5, 10), padx=10, anchor="w")

remove_timestamps_switch = ctk.CTkSwitch(settings_frame, text="Remove timestamps and IDs", state="disabled")
remove_timestamps_switch.pack(pady=(5, 10), padx=10, anchor="w")

# ===== OUTPUT FOLDER =====
folder_frame = ctk.CTkFrame(app, corner_radius=10)
folder_frame.pack(pady=(0, 15), padx=20, fill="x")

ctk.CTkLabel(folder_frame, text="Output Folder:", anchor="w").pack(pady=(10, 0), padx=10, fill="x")

inner_folder_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
inner_folder_frame.pack(pady=(5, 10), padx=10, fill="x")

folder_var = ctk.StringVar(value=config["default_output_folder"])
folder_entry = ctk.CTkEntry(inner_folder_frame, textvariable=folder_var, state="readonly")
folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

folder_button = ctk.CTkButton(inner_folder_frame, text="📂 Choose Folder", command=choose_folder, state="disabled", width=120)
folder_button.pack(side="left")

# ===== FILENAME TEMPLATE =====
filename_frame = ctk.CTkFrame(app, corner_radius=10)
filename_frame.pack(pady=(0, 15), padx=20, fill="x")

ctk.CTkLabel(filename_frame, text="Filename Template (use {UNIX_TIMESTAMP} and {VIDEO_ID}):", anchor="w").pack(pady=(10, 0), padx=10, fill="x")

filename_entry = ctk.CTkEntry(
    filename_frame,
    textvariable=ctk.StringVar(value=config["default_filename_template"]),
    state="disabled"
)
filename_entry.pack(
    pady=(5, 10),
    padx=10,
    fill="x",
    expand=True
)

# ===== DOWNLOAD BUTTON =====
download_button = ctk.CTkButton(app, text="⬇ Download and Save Transcript", command=save_transcript, width=400, height=60, state="disabled")
download_button.pack(pady=(20, 20))

# ===== SETTINGS BUTTON =====
menu_bar = ctk.CTkFrame(app, fg_color="transparent")
menu_bar.place(relx=1, rely=0, anchor="ne", x=-10, y=10)
settings_button = ctk.CTkButton(menu_bar, text="⚙ Settings", width=100, command=open_settings_window)
settings_button.pack()

app.mainloop()
