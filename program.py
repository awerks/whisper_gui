import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import requests
import os
import subprocess
import threading
from typing import Any

WHISPER_API_URL: str = "https://api.openai.com/v1/audio/transcriptions"
API_KEY: str = os.getenv("OPENAI_TRANSCRIPTION_KEY")


def select_file() -> None:
    """Open a file dialog to select an audio file and update the file path entry."""
    file_path: str = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.flac"), ("All Files", "*.*")]
    )
    if file_path:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)


def compress_file(file_path: str, compressed_path: str = "compressed_audio.mp3") -> str:
    """Compress the audio file using ffmpeg.

    Args:
        file_path: The path to the original audio file.
        compressed_path: The path to save the compressed audio file.

    Returns:
        The path to the compressed audio file.

    Raises:
        subprocess.CalledProcessError: If ffmpeg fails to compress the file.
    """
    popen: subprocess.Popen = subprocess.Popen(
        ["ffmpeg", "-i", file_path, "-b:a", "64k", compressed_path, "-y"],
    )
    stdout, stderr = popen.communicate()
    if popen.returncode != 0:
        raise subprocess.CalledProcessError(popen.returncode, popen.args, output=stdout, stderr=stderr)
    return compressed_path


def send_transcription_request_sync(file_path: str, is_compressed: bool = False) -> None:
    """Send a transcription request to the Whisper API synchronously.

    Args:
        file_path: The path to the audio file to transcribe.
        is_compressed: Indicates whether the file was compressed.
    """
    status_label.config(text="Transcribing, please wait...", foreground="lightblue")
    root.update()

    try:
        with open(file_path, "rb") as audio_file:
            response = requests.post(
                WHISPER_API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                data={"model": "whisper-1"},
                files={"file": audio_file},
            )

        if response.status_code == 200:
            response_json: dict[str, Any] = response.json()
            transcription: str = response_json.get("text", "No transcription available.")
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, transcription)
            status_label.config(text="Transcription completed successfully!", foreground="lightgreen")
            copy_button.config(state="normal")
        else:
            messagebox.showerror("API Error", f"Error: {response.status_code}\n{response.text}")
            status_label.config(text="Failed to transcribe.", foreground="red")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        status_label.config(text="Error occurred.", foreground="red")
    finally:
        if is_compressed:
            os.remove(file_path)


def transcribe_file() -> None:
    """Handle file selection, compression if needed, and start transcription."""
    file_path: str = file_path_entry.get()
    compressed_path: str = "compressed_audio.mp3"
    is_compressed: bool = False
    if not file_path:
        messagebox.showerror("Error", "Please select a file to transcribe.")
        return

    if os.path.getsize(file_path) > 25 * 1024 * 1024:  # 25 MB in bytes
        messagebox.showinfo(
            "Compression Notice",
            "The file is larger than 25 MB and will be compressed.",
        )
        try:
            status_label.config(text="Compressing file...", foreground="lightblue")
            root.update()
            file_path = compress_file(file_path, compressed_path)
            is_compressed = True
        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                "Compression Error",
                f"An error occurred while compressing the file: {e}",
            )
            status_label.config(text="Compression failed.", foreground="red")
            return

    threading.Thread(target=send_transcription_request_sync, args=(file_path, is_compressed)).start()


def copy_to_clipboard() -> None:
    """Copy the transcription text to the clipboard."""
    transcription_text: str = result_text.get("1.0", tk.END).strip()
    root.clipboard_clear()
    root.clipboard_append(transcription_text)
    messagebox.showinfo("Copied", "Transcription copied to clipboard!")


def center_window(root: tk.Tk, width: int = 600, height: int = 500) -> None:
    """Center the window on the screen.

    Args:
        root: The root Tkinter window.
        width: The desired width of the window.
        height: The desired height of the window.
    """
    screen_width: int = root.winfo_screenwidth()
    screen_height: int = root.winfo_screenheight()

    x: int = (screen_width // 2) - (width // 2)
    y: int = (screen_height // 2) - (height // 2)

    root.geometry(f"{width}x{height}+{x}+{y}")


root: tk.Tk = tk.Tk()
center_window(root, 600, 500)

root.title("Whisper GUI")
root.configure(background="#1e1e1e")
root.resizable(False, False)

style: ttk.Style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#1e1e1e")
style.configure(
    "TLabel",
    background="#1e1e1e",
    foreground="white",
    font=("JetBrains Mono", 12),
)
style.configure(
    "Header.TLabel",
    background="#1e1e1e",
    foreground="#f8f8f2",
    font=("JetBrains Mono", 16, "bold"),
)
style.configure(
    "TButton",
    background="#50fa7b",
    foreground="black",
    font=("JetBrains Mono", 12),
)
style.map("TButton", background=[("active", "#45a049")])
style.configure(
    "TEntry",
    background="#3c3c3e",
    foreground="white",
    font=("JetBrains Mono", 12),
)
style.configure(
    "Status.TLabel",
    background="#1e1e1e",
    foreground="white",
    font=("JetBrains Mono", 10),
)
header_label: ttk.Label = ttk.Label(root, text="Audio Transcription Tool", style="Header.TLabel")
header_label.pack(pady=10)

frame: ttk.Frame = ttk.Frame(root)
frame.pack(pady=10)
file_path_label: ttk.Label = ttk.Label(frame, text="Select a file:")
file_path_label.grid(row=0, column=0, padx=5)
file_path_entry: ttk.Entry = ttk.Entry(frame, width=40, foreground="black")
file_path_entry.grid(row=0, column=1, padx=5)
browse_button: ttk.Button = ttk.Button(frame, text="Browse", command=select_file)
browse_button.grid(row=0, column=2, padx=5)

status_label: ttk.Label = ttk.Label(root, text="", style="Status.TLabel")
status_label.pack(pady=5)

transcribe_button: ttk.Button = ttk.Button(root, text="Transcribe", command=transcribe_file)
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

copy_button: ttk.Button = ttk.Button(root, text="Copy to Clipboard", command=copy_to_clipboard, state="disabled")
copy_button.pack(pady=10)

root.mainloop()
