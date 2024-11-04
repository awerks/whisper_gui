import tkinter as tk
import requests
import os
import json
import subprocess
from platform import system
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Any
from datetime import datetime
from utils import write_srt, compress_file, download_url, extract_audio

WHISPER_API_URL: str = "https://api.openai.com/v1/audio/transcriptions"
API_KEY: str = os.getenv("OPENAI_TRANSCRIPTION_KEY")
UI_LANGUAGE = "en"

# default download directory (Windows/MacOS/Linux)

if system() == "Windows":
    OUTPUT_DIR = os.path.join(os.getenv("USERPROFILE"), "Downloads")
else:
    OUTPUT_DIR = os.path.join(os.getenv("HOME"), "Downloads")

with open("translations.json", "r", encoding="utf-8") as f:
    translations = json.load(f)


def translate(key: str) -> str:
    return translations[UI_LANGUAGE].get(key, key)


def switch_language(lang: str) -> None:
    # sorry
    global UI_LANGUAGE
    UI_LANGUAGE = lang
    update_ui_texts()


def update_ui_texts() -> None:
    root.title(translate("title"))
    transcribe_button.config(text=translate("transcribe_button"))
    copy_button.config(text=translate("copy_button"))
    file_path_label.config(text=translate("file_or_url_label"))
    browse_button.config(text=translate("browse_button"))
    c1.config(text=translate("subtitles_checkbox"))
    status_label.config(text=translate("status_label"))
    root.update()


def select_file() -> None:
    """Open a file dialog to select an audio file and update the file path entry."""
    filetypes = [
        ("Audio/Video Files", "*.mp3 *.wav *.m4a *.flac *.mp4 *.mkv *.webm *.avi *.flv *.mov *.wmv"),
        ("All Files", "*.*"),
    ]
    file_path_or_url: str = filedialog.askopenfilename(
        filetypes=filetypes,
    )
    if file_path_or_url:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path_or_url)


def send_transcription_request(file_path_or_url: str, is_compressed: bool = False) -> None:
    """Send a transcription request to the Whisper API synchronously."""
    status_label.config(text=translate("transcribing_wait"), foreground="lightblue")
    root.update()
    try:
        with open(file_path_or_url, "rb") as audio_file:
            response = requests.post(
                WHISPER_API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                data={"model": "whisper-1", "response_format": "verbose_json"},
                files={"file": audio_file},
            )
        if response.status_code == 200:
            response_json: dict[str, Any] = response.json()
            transcription: str = response_json.get("text", translate("no_transcription"))
            language = response_json.get("language", "english")
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, transcription)
            status_label.config(
                text=translate("transcription_success").format(language=language.capitalize()),
                foreground="lightgreen",
            )
            copy_button.config(state="normal")
            if include_subtitles.get():
                current_time = datetime.now().strftime("%Y_%m_%d-%p%I_%M_%S")
                with open(os.path.join(OUTPUT_DIR, f"subtitles_{language}_{current_time}.srt"), "w") as srt:
                    write_srt(response_json["segments"], file=srt)
                messagebox.showinfo(translate("subtitles"), translate("subtitles_saved"))
        else:
            messagebox.showerror(
                translate("transcription_error"),
                translate("transcription_error_message").format(
                    status_code=response.status_code, error_text=response.text
                ),
            )
            status_label.config(text=translate("transcription_failed"), foreground="red")
    except Exception as e:
        messagebox.showerror(translate("error"), translate("transcription_error_occurred").format(error=e))
        status_label.config(text=translate("transcription_error_occurred"), foreground="red")
    finally:
        if is_compressed:
            os.remove(file_path_or_url)


def transcribe_file() -> None:
    """Handle file selection, URL download and audio extraction, compression if needed, and start transcription."""
    file_path_or_url: str = file_path_entry.get()
    compressed_path: str = "compressed_audio.mp3"
    is_compressed: bool = False
    if not file_path_or_url:
        messagebox.showerror(translate("error"), translate("no_file_selected_error"))
        return
    current_time = datetime.now().strftime("%Y_%m_%d-%p%I_%M_%S")

    # if it's a URL, download the video and extract the audio
    if "http" in file_path_or_url:
        try:
            video_path = os.path.join(OUTPUT_DIR, f"downloaded_video_{current_time}.mp4")

            status_label.config(text=translate("downloading_video"), foreground="lightblue")
            root.update()
            file_path_or_url = download_url(file_path_or_url, video_path)

        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                translate("download_error"),
                translate("download_error_message").format(error=e),
            )
            status_label.config(text=translate("download_failed"), foreground="red")
            return

    if any(ext in file_path_or_url for ext in ["mp4", "mkv", "webm", "avi", "flv", "mov", "wmv"]):
        audio_path = os.path.join(OUTPUT_DIR, f"extracted_audio_{current_time}.mp3")
        try:
            status_label.config(text=translate("extracting_audio"), foreground="lightblue")
            root.update()
            file_path_or_url = extract_audio(file_path_or_url, audio_path)
        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                translate("extraction_error"),
                translate("extraction_error_message").format(error=e),
            )
            status_label.config(text=translate("extraction_failed"), foreground="red")
            return

    if os.path.getsize(file_path_or_url) > 25 * 1024 * 1024:  # 25 MB in bytes
        messagebox.showinfo(
            translate("compression_notice"),
            translate("compression_message"),
        )
        try:
            status_label.config(text=translate("compressing_file"), foreground="lightblue")
            root.update()
            file_path_or_url = compress_file(file_path_or_url, compressed_path)
            is_compressed = True
        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                translate("compression_error"),
                translate("compression_error_message").format(error=e),
            )
            status_label.config(text=translate("compression_failed"), foreground="red")
            return

    send_transcription_request(file_path_or_url, is_compressed)


def copy_to_clipboard() -> None:
    """Copy the transcription text to the clipboard."""
    transcription_text: str = result_text.get("1.0", tk.END).strip()
    root.clipboard_clear()
    root.clipboard_append(transcription_text)
    messagebox.showinfo(translate("copied"), translate("copied_message"))


def center_window(root: tk.Tk, width: int = 600, height: int = 500) -> None:
    """Center the window on the screen."""
    screen_width: int = root.winfo_screenwidth()
    screen_height: int = root.winfo_screenheight()

    x: int = (screen_width // 2) - (width // 2)
    y: int = (screen_height // 2) - (height // 2)

    root.geometry(f"{width}x{height}+{x}+{y}")


root: tk.Tk = tk.Tk()
center_window(root, 600, 500)

# Update UI elements with translations
root.title(translate("title"))

header_label: ttk.Label = ttk.Label(root, text=translate("title"), style="Header.TLabel")
header_label.pack(pady=10)

frame: ttk.Frame = ttk.Frame(root)
frame.pack(pady=10)
file_path_label: ttk.Label = ttk.Label(frame, text=translate("file_or_url_label"))
file_path_label.grid(row=0, column=0, padx=5)
file_path_entry: ttk.Entry = ttk.Entry(frame, width=40, foreground="white")
file_path_entry.grid(row=0, column=1, padx=5)
browse_button: ttk.Button = ttk.Button(frame, text=translate("browse_button"), command=select_file)
browse_button.grid(row=0, column=2, padx=5)

status_label: ttk.Label = ttk.Label(root, text=translate("status_label"), style="Status.TLabel")
status_label.pack(pady=5)
include_subtitles = tk.IntVar()
c1 = tk.Checkbutton(
    root,
    text=translate("subtitles_checkbox"),
    variable=include_subtitles,
    onvalue=1,
    offvalue=0,
)
c1.pack(pady=5)
transcribe_button: ttk.Button = ttk.Button(root, text=translate("transcribe_button"), command=transcribe_file)
transcribe_button.pack(pady=15)

text_frame: ttk.Frame = ttk.Frame(root)
text_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

result_text: tk.Text = tk.Text(
    text_frame,
    height=10,
    wrap="word",
    font=("JetBrains Mono", 12),
    background="#3c3c3e",
    foreground="white",
    borderwidth=0,
)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar: ttk.Scrollbar = ttk.Scrollbar(text_frame, command=result_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

result_text.config(yscrollcommand=scrollbar.set)

copy_button: ttk.Button = ttk.Button(root, text=translate("copy_button"), command=copy_to_clipboard, state="disabled")
copy_button.pack(pady=10)

# Add language switch buttons
language_frame: ttk.Frame = ttk.Frame(root)
language_frame.pack(pady=10)
english_button: ttk.Button = ttk.Button(language_frame, text="English", command=lambda: switch_language("en"))
english_button.grid(row=0, column=0, padx=5)
ukrainian_button: ttk.Button = ttk.Button(language_frame, text="Українська", command=lambda: switch_language("uk"))
ukrainian_button.grid(row=0, column=1, padx=5)

root.mainloop()
